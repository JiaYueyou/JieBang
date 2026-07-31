"""Evaluate Phase 2 retrieval quality against the engineering golden set."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import (
    RETRIEVAL_RELATIVE_SCORE_WINDOW,
    RETRIEVAL_SEMANTIC_SCORE_FLOOR,
)
from app.core.database import async_session, engine
from app.core.time import utc_isoformat, utc_now
from app.domain.data_quality import (
    normalize_job_body,
    simhash64,
    simhash_similarity,
)
from app.evaluation.phase2_golden import validate_dataset
from app.schemas.retrieval import RetrievalSearchRequest
from app.services.retrieval_service import RetrievalService

DEFAULT_GOLDEN_PATH = (
    BACKEND_ROOT / "evaluation" / "phase2_retrieval_golden_set.json"
)
DEFAULT_REPORT_JSON = (
    BACKEND_ROOT / "evaluation" / "phase2_retrieval_report.json"
)
DEFAULT_REPORT_MD = (
    BACKEND_ROOT / "evaluation" / "phase2_retrieval_report.md"
)
NEAR_DUPLICATE_THRESHOLD = 0.9
EVALUATION_TOP_K = 10
METRIC_THRESHOLDS = {
    "recall_at_5": 0.85,
    "mrr_at_10": 0.75,
    "citation_precision_at_5": 0.95,
    "top1_expected_accuracy": 0.8,
    "no_answer_accuracy": 0.9,
    "filter_violation_rate": 0.0,
    "duplicate_negative_fpr": 0.05,
    "warm_latency_p95_ms": 500,
}


class _PrefetchedEmbeddingProvider:
    """Reuse one batched embedding call across deterministic evaluation cases."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.name = delegate.name
        self.model = delegate.model
        self.dimension = delegate.dimension
        self._cache: dict[str, list[float]] = {}

    async def prefetch(self, texts: list[str]) -> None:
        unique = list(dict.fromkeys(texts))
        vectors = await self.delegate.embed_texts(unique)
        self._cache.update(zip(unique, vectors))

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        missing = [
            text
            for text in dict.fromkeys(texts)
            if text not in self._cache
        ]
        if missing:
            vectors = await self.delegate.embed_texts(missing)
            self._cache.update(zip(missing, vectors))
        return [self._cache[text] for text in texts]


def _mean(values: list[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[rank]


def _duplicate_prediction(case: dict[str, Any]) -> dict[str, Any]:
    existing = case["input"]["existing"]
    candidate = case["input"]["candidate"]
    similarity = simhash_similarity(
        simhash64(normalize_job_body(existing["jd_text"])),
        simhash64(normalize_job_body(candidate["jd_text"])),
    )
    predicted_duplicate = similarity >= NEAR_DUPLICATE_THRESHOLD
    expected_duplicate = bool(case["expected"]["duplicate"])
    return {
        "id": case["id"],
        "similarity": similarity,
        "threshold": NEAR_DUPLICATE_THRESHOLD,
        "expected_duplicate": expected_duplicate,
        "predicted_duplicate": predicted_duplicate,
        "passed": predicted_duplicate == expected_duplicate,
    }


def _filter_violations(
    filters: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for item in items:
        reasons: list[str] = []
        if (
            filters.get("standard_job_id") is not None
            and item["standard_job_id"] != filters["standard_job_id"]
        ):
            reasons.append("standard_job_id")
        if (
            filters.get("skill_ids")
            and item["skill_id"] not in filters["skill_ids"]
        ):
            reasons.append("skill_ids")
        if (
            filters.get("source_platforms")
            and item["source_platform"] not in filters["source_platforms"]
        ):
            reasons.append("source_platforms")
        if (
            filters.get("minimum_quality_score") is not None
            and item["quality_score"]
            < float(filters["minimum_quality_score"])
        ):
            reasons.append("minimum_quality_score")
        if reasons:
            violations.append(
                {
                    "evidence_id": item["evidence_id"],
                    "fields": reasons,
                }
            )
    return violations


def _retrieval_metrics(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    grounded = [row for row in rows if row["expected_evidence_ids"]]
    no_answer = [row for row in rows if not row["expected_evidence_ids"]]
    returned_item_count = sum(
        len(row["returned_evidence_ids"]) for row in rows
    )
    violation_count = sum(
        len(row["filter_violations"]) for row in rows
    )
    latencies = [row["latency_ms"] for row in rows]
    return {
        "grounded_case_count": len(grounded),
        "no_answer_case_count": len(no_answer),
        "recall_at_5": _mean(
            [float(row["recall_at_5"]) for row in grounded]
        ),
        "mrr_at_10": _mean(
            [float(row["reciprocal_rank_at_10"]) for row in grounded]
        ),
        "citation_precision_at_5": _mean(
            [
                float(row["citation_precision_at_5"])
                for row in grounded
            ]
        ),
        "top1_expected_accuracy": _mean(
            [1.0 if row["top1_expected"] else 0.0 for row in grounded]
        ),
        "no_answer_accuracy": _mean(
            [
                1.0 if row["no_answer_correct"] else 0.0
                for row in no_answer
            ]
        ),
        "filter_violation_rate": (
            round(violation_count / returned_item_count, 6)
            if returned_item_count
            else 0.0
        ),
        "warm_latency_p50_ms": (
            int(statistics.median(latencies)) if latencies else 0
        ),
        "warm_latency_p95_ms": _percentile(latencies, 0.95),
        "warm_latency_max_ms": max(latencies, default=0),
    }


async def _evaluate_retrieval_cases(
    cases: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    async with async_session() as session:
        base_service = RetrievalService(session)
        index = await base_service._resolve_index(None)
        embedding_metadata = {
            "provider": index.embedding_provider,
            "model": index.embedding_model,
            "dimension": index.embedding_dimension,
        }
        provider = _PrefetchedEmbeddingProvider(
            base_service._provider_for_index(index)
        )
        await provider.prefetch(
            ["Java", *[case["query"] for case in cases]]
        )
        service = RetrievalService(
            session,
            embedding_provider=provider,
            vector_store=base_service.vector_store,
        )
        await service.search(
            RetrievalSearchRequest(query="Java", top_k=1),
            user_id=1,
            log_query=False,
        )
        rows: list[dict[str, Any]] = []
        for case in cases:
            payload = RetrievalSearchRequest(
                query=case["query"],
                top_k=EVALUATION_TOP_K,
                **case["filters"],
            )
            response = await service.search(
                payload,
                user_id=1,
                log_query=False,
            )
            items = [
                item.model_dump(mode="json") for item in response.items
            ]
            returned_ids = [item["evidence_id"] for item in items]
            top5_ids = returned_ids[:5]
            expected_ids = list(case["expected_evidence_ids"])
            expected_set = set(expected_ids)
            top5_hits = [
                evidence_id
                for evidence_id in top5_ids
                if evidence_id in expected_set
            ]
            violations = _filter_violations(case["filters"], items)
            if expected_ids:
                recall_at_5 = len(set(top5_hits)) / len(expected_set)
                citation_precision_at_5 = (
                    len(top5_hits) / len(top5_ids) if top5_ids else 0.0
                )
                reciprocal_rank = next(
                    (
                        1 / rank
                        for rank, evidence_id in enumerate(
                            returned_ids[:10],
                            start=1,
                        )
                        if evidence_id in expected_set
                    ),
                    0.0,
                )
                top1_expected = bool(
                    returned_ids and returned_ids[0] in expected_set
                )
                no_answer_correct = None
                passed = bool(top5_hits) and not violations
            else:
                recall_at_5 = None
                citation_precision_at_5 = None
                reciprocal_rank = None
                top1_expected = None
                no_answer_correct = not returned_ids
                passed = no_answer_correct and not violations
            rows.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "split": case["split"],
                    "evaluation_group": case.get("evaluation_group"),
                    "query": case["query"],
                    "filters": case["filters"],
                    "answer_mode": case["answer_mode"],
                    "expected_evidence_ids": expected_ids,
                    "returned_evidence_ids": returned_ids,
                    "recall_at_5": (
                        round(recall_at_5, 6)
                        if recall_at_5 is not None
                        else None
                    ),
                    "reciprocal_rank_at_10": (
                        round(reciprocal_rank, 6)
                        if reciprocal_rank is not None
                        else None
                    ),
                    "citation_precision_at_5": (
                        round(citation_precision_at_5, 6)
                        if citation_precision_at_5 is not None
                        else None
                    ),
                    "top1_expected": top1_expected,
                    "no_answer_correct": no_answer_correct,
                    "filter_violations": violations,
                    "latency_ms": response.latency_ms,
                    "index_version": response.index_version,
                    "backend": response.backend,
                    "warnings": response.warnings,
                    "passed": passed,
                }
            )

    return rows, _retrieval_metrics(rows), embedding_metadata


def _category_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    result: dict[str, Any] = {}
    for category, category_rows in grouped.items():
        grounded = [
            row for row in category_rows if row["expected_evidence_ids"]
        ]
        no_answer = [
            row for row in category_rows if not row["expected_evidence_ids"]
        ]
        result[category] = {
            "case_count": len(category_rows),
            "pass_rate": _mean(
                [1.0 if row["passed"] else 0.0 for row in category_rows]
            ),
            "recall_at_5": (
                _mean(
                    [float(row["recall_at_5"]) for row in grounded]
                )
                if grounded
                else None
            ),
            "mrr_at_10": (
                _mean(
                    [
                        float(row["reciprocal_rank_at_10"])
                        for row in grounded
                    ]
                )
                if grounded
                else None
            ),
            "no_answer_accuracy": (
                _mean(
                    [
                        1.0 if row["no_answer_correct"] else 0.0
                        for row in no_answer
                    ]
                )
                if no_answer
                else None
            ),
        }
    return result


def _threshold_results(metrics: dict[str, Any]) -> dict[str, bool]:
    return {
        "recall_at_5": (
            metrics["recall_at_5"] >= METRIC_THRESHOLDS["recall_at_5"]
        ),
        "mrr_at_10": (
            metrics["mrr_at_10"] >= METRIC_THRESHOLDS["mrr_at_10"]
        ),
        "citation_precision_at_5": (
            metrics["citation_precision_at_5"]
            >= METRIC_THRESHOLDS["citation_precision_at_5"]
        ),
        "top1_expected_accuracy": (
            metrics["top1_expected_accuracy"]
            >= METRIC_THRESHOLDS["top1_expected_accuracy"]
        ),
        "no_answer_accuracy": (
            metrics["no_answer_accuracy"]
            >= METRIC_THRESHOLDS["no_answer_accuracy"]
        ),
        "filter_violation_rate": (
            metrics["filter_violation_rate"]
            <= METRIC_THRESHOLDS["filter_violation_rate"]
        ),
        "duplicate_negative_fpr": (
            metrics["duplicate_negative_fpr"]
            <= METRIC_THRESHOLDS["duplicate_negative_fpr"]
        ),
        "warm_latency_p95_ms": (
            metrics["warm_latency_p95_ms"]
            <= METRIC_THRESHOLDS["warm_latency_p95_ms"]
        ),
    }


async def evaluate(golden_path: Path) -> dict[str, Any]:
    raw = golden_path.read_bytes()
    golden = json.loads(raw.decode("utf-8"))
    validate_dataset(golden)
    duplicate_rows = [
        _duplicate_prediction(case)
        for case in golden["duplicate_negative_cases"]
    ]
    retrieval_rows, metrics, embedding_metadata = await _evaluate_retrieval_cases(
        golden["retrieval_cases"]
    )
    false_positive_count = sum(
        row["predicted_duplicate"] for row in duplicate_rows
    )
    duplicate_negative_fpr = round(
        false_positive_count / len(duplicate_rows),
        6,
    )
    metrics["duplicate_negative_fpr"] = duplicate_negative_fpr
    threshold_results = _threshold_results(metrics)
    coverage_gate = bool(golden["coverage_gate"])
    split_metrics: dict[str, dict[str, Any]] = {}
    split_threshold_results: dict[str, dict[str, bool]] = {}
    split_performance_gates: dict[str, bool] = {}
    for split in ("development", "validation", "test"):
        split_rows = [
            row for row in retrieval_rows if row["split"] == split
        ]
        if not split_rows:
            continue
        split_result = _retrieval_metrics(split_rows)
        split_result["duplicate_negative_fpr"] = duplicate_negative_fpr
        split_metrics[split] = split_result
        split_threshold_results[split] = _threshold_results(split_result)
        split_performance_gates[split] = all(
            split_threshold_results[split].values()
        )
    performance_gate = (
        all(
            split_performance_gates.get(split, False)
            for split in ("validation", "test")
        )
        if coverage_gate
        else all(threshold_results.values())
    )
    release_gate = performance_gate and coverage_gate
    index_versions = sorted(
        {row["index_version"] for row in retrieval_rows}
    )
    backends = sorted({row["backend"] for row in retrieval_rows})
    return {
        "schema_version": "phase2-retrieval-eval-v1",
        "generated_at": utc_isoformat(utc_now()),
        "golden_set": str(golden_path.relative_to(BACKEND_ROOT)),
        "golden_set_sha256": hashlib.sha256(raw).hexdigest(),
        "evaluation_top_k": EVALUATION_TOP_K,
        "retrieval_policy": {
            "relative_score_window": RETRIEVAL_RELATIVE_SCORE_WINDOW,
            "semantic_score_floor": RETRIEVAL_SEMANTIC_SCORE_FLOOR,
        },
        "embedding": embedding_metadata,
        "index_versions": index_versions,
        "backends": backends,
        "coverage": golden["coverage"],
        "split_policy": golden["split_policy"],
        "review_summary": golden["review_summary"],
        "metric_definitions": {
            "recall_at_5": (
                "Macro average of relevant golden evidence IDs returned in "
                "the first 5 divided by all expected IDs (at most 5/case)."
            ),
            "mrr_at_10": (
                "Macro mean reciprocal rank of the first expected evidence "
                "ID in the first 10 results."
            ),
            "citation_precision_at_5": (
                "Macro average of first-5 result IDs present in the case's "
                "expected evidence IDs."
            ),
            "no_answer_accuracy": (
                "Share of insufficient-evidence cases returning zero items."
            ),
            "filter_violation_rate": (
                "Returned items violating any declared structured filter "
                "divided by all returned items."
            ),
            "duplicate_negative_fpr": (
                "Distinct synthetic role pairs classified as near duplicate "
                f"at SimHash similarity >= {NEAR_DUPLICATE_THRESHOLD}."
            ),
            "warm_latency_p95_ms": (
                "Nearest-rank P95 of service-reported latency after one "
                "unmeasured warm-up query."
            ),
        },
        "thresholds": METRIC_THRESHOLDS,
        "metrics": metrics,
        "threshold_results": threshold_results,
        "split_metrics": split_metrics,
        "split_threshold_results": split_threshold_results,
        "split_performance_gates": split_performance_gates,
        "performance_gate": performance_gate,
        "coverage_gate": coverage_gate,
        "release_gate": release_gate,
        "overall_assessment": (
            "ready_to_share"
            if release_gate
            else (
                "share_with_caveats"
                if performance_gate
                else "needs_revision"
            )
        ),
        "category_metrics": _category_metrics(retrieval_rows),
        "duplicate_negative_cases": duplicate_rows,
        "retrieval_cases": retrieval_rows,
        "limitations": [
            (
                "The retrieval set is deterministically generated from "
                "foreign-key-linked MySQL evidence and engineering-reviewed; "
                "it is not human domain gold."
            ),
            (
                "Retrieval cases are grouped by standard job into development, "
                "validation and test; the split job IDs are recorded in the "
                "report."
                if coverage_gate
                else (
                    "All retrieval cases remain in the development split "
                    "until the corpus covers at least 5 jobs, 20 skills and "
                    "2 sources."
                )
            ),
            (
                "The current embedding is "
                f"{embedding_metadata['model']} at "
                f"{embedding_metadata['dimension']} dimensions through "
                f"{embedding_metadata['provider']}."
            ),
            (
                "Only the development jobs were used for the final retriever "
                "tuning pass; the replacement validation and test jobs were "
                "frozen before their first evaluation."
                if coverage_gate
                else (
                    "Scores on this development set were used to diagnose "
                    "the retriever and do not estimate unseen-query "
                    "performance."
                )
            ),
        ],
    }


def _markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    failed_thresholds = [
        name
        for name, passed in report["threshold_results"].items()
        if not passed
    ]
    failed_cases = [
        row for row in report["retrieval_cases"] if not row["passed"]
    ]
    assessment_labels = {
        "ready_to_share": "Ready to share",
        "share_with_caveats": "Share with caveats",
        "needs_revision": "Needs revision",
    }
    split_labels = {
        "development": "开发",
        "validation": "验证",
        "test": "冻结测试",
    }
    split_lines = [
        "## 分区指标",
        "",
        "| 分区 | 样本数 | Recall@5 | Citation Precision@5 | "
        "拒答准确率 | P95 | 门禁 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for split in ("development", "validation", "test"):
        split_metric = report["split_metrics"].get(split)
        if not split_metric:
            continue
        split_lines.append(
            f"| {split_labels[split]} | "
            f"{split_metric['grounded_case_count'] + split_metric['no_answer_case_count']} | "
            f"{split_metric['recall_at_5']:.2%} | "
            f"{split_metric['citation_precision_at_5']:.2%} | "
            f"{split_metric['no_answer_accuracy']:.2%} | "
            f"{split_metric['warm_latency_p95_ms']}ms | "
            f"{report['split_performance_gates'][split]} |"
        )
    split_lines.append("")
    return "\n".join(
        [
            "# FYZ Phase 2 检索评测报告",
            "",
            (
                "## Overall Assessment: "
                f"{assessment_labels[report['overall_assessment']]}"
            ),
            "",
            f"- 生成时间：`{report['generated_at']}`",
            f"- 索引版本：`{', '.join(report['index_versions'])}`",
            f"- 检索后端：`{', '.join(report['backends'])}`",
            (
                "- Embedding："
                f"`{report['embedding']['model']} / "
                f"{report['embedding']['dimension']}d / "
                f"{report['embedding']['provider']}`"
            ),
            f"- Recall@5：`{metrics['recall_at_5']:.2%}`",
            f"- MRR@10：`{metrics['mrr_at_10']:.2%}`",
            (
                "- Citation Precision@5："
                f"`{metrics['citation_precision_at_5']:.2%}`"
            ),
            (
                "- Top-1 命中率："
                f"`{metrics['top1_expected_accuracy']:.2%}`"
            ),
            (
                "- 拒答准确率："
                f"`{metrics['no_answer_accuracy']:.2%}`"
            ),
            (
                "- 过滤违规率："
                f"`{metrics['filter_violation_rate']:.2%}`"
            ),
            (
                "- 近重复负样本误报率："
                f"`{metrics['duplicate_negative_fpr']:.2%}`"
            ),
            (
                "- 暖态延迟 P50 / P95 / Max："
                f"`{metrics['warm_latency_p50_ms']} / "
                f"{metrics['warm_latency_p95_ms']} / "
                f"{metrics['warm_latency_max_ms']} ms`"
            ),
            "",
            "## 发布门禁",
            "",
            f"- 性能门禁：`{report['performance_gate']}`",
            f"- 覆盖门禁：`{report['coverage_gate']}`",
            f"- 最终发布门禁：`{report['release_gate']}`",
            (
                "- 未达阈值指标："
                f"`{', '.join(failed_thresholds) if failed_thresholds else '无'}`"
            ),
            f"- 未通过检索样本：`{len(failed_cases)}`",
            "",
            *split_lines,
            "## 方法与边界",
            "",
            (
                "- 指标均由冻结 JSON 输入重算，报告记录 Golden Set "
                "SHA-256、索引版本、检索后端和逐样本结果。"
            ),
            (
                "- 当前覆盖为 "
                f"{report['coverage']['standard_job_count']} 个标准岗位、"
                f"{report['coverage']['skill_count']} 个技能、"
                f"{report['coverage']['source_platform_count']} 个来源；"
                "未满足覆盖门禁时不得升级为发布测试集。"
            ),
            (
                "- 样本仅经过透明工程审核，`human_domain_gold=false`，"
                "不能宣称为业务专家金标。"
            ),
            (
                "- 当前向量为 "
                f"`{report['embedding']['model']}` "
                f"（{report['embedding']['dimension']} 维，"
                f"{report['embedding']['provider']}）。"
            ),
            (
                "- 本报告属于开发集闭环评测，结果已用于诊断排序；"
                "在形成按岗位隔离的冻结测试集前，不代表未见查询表现。"
            ),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLDEN_PATH,
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_REPORT_JSON,
    )
    parser.add_argument(
        "--report-markdown",
        type=Path,
        default=DEFAULT_REPORT_MD,
    )
    args = parser.parse_args()

    async def run() -> dict[str, Any]:
        try:
            return await evaluate(args.golden.resolve())
        finally:
            await engine.dispose()

    report = asyncio.run(run())
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.report_markdown.write_text(
        _markdown(report),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "performance_gate": report["performance_gate"],
                "coverage_gate": report["coverage_gate"],
                "release_gate": report["release_gate"],
                "json": str(args.report_json),
                "markdown": str(args.report_markdown),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
