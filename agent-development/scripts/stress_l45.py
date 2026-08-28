"""Repeatable L4/L5 stability and quality acceptance runner.

Offline simulation is the default so CI never needs an external model. Pass
``--live`` to exercise the configured DeepSeek endpoint from the backend.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_SRC = ROOT / "agent-development" / "src"
BACKEND = ROOT / "fyz-src" / "backend"
sys.path.insert(0, str(AGENT_SRC))

from jiebang_agents.graph_enrichment import (  # noqa: E402
    GraphEnrichmentOutput,
    KnowledgePointOutput,
    SkillGraphCompletionAgent,
    SkillGraphCompletionInput,
    TechPointOutput,
    evaluate_l45_output,
    nearest_rank_percentile,
)


class SimulatedHTTPResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": json.dumps(_valid_output())}}]}


class RecoverableFailureTransport:
    """AsyncClient replacement that raises real httpx timeouts on schedule."""

    def __init__(self, httpx_module, fail_every: int) -> None:
        self.httpx = httpx_module
        self.fail_every = max(0, fail_every)
        self.calls = 0

    def client_type(self):
        transport = self

        class SimulatedHTTPClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                transport.calls += 1
                if transport.fail_every and transport.calls % transport.fail_every == 0:
                    request = transport.httpx.Request("POST", "https://offline.test")
                    raise transport.httpx.ReadTimeout(
                        "injected recoverable timeout", request=request
                    )
                return SimulatedHTTPResponse()

        return SimulatedHTTPClient


def _valid_output() -> dict:
    return GraphEnrichmentOutput(
        skill_name="Python",
        tech_points=[TechPointOutput(
            name="FastAPI",
            category="framework",
            detail="异步 Web API 框架",
            confidence=.9,
            evidence_ids=["evidence-a", "evidence-b"],
            knowledge_points=[KnowledgePointOutput(
                name="依赖注入",
                description="通过依赖图复用并隔离请求资源",
                difficulty="medium",
                confidence=.88,
                evidence_ids=["evidence-a", "evidence-b"],
            )],
        )],
    ).model_dump(mode="json")


def _request(index: int) -> SkillGraphCompletionInput:
    return SkillGraphCompletionInput(
        job_directions=["Python 后端工程师"],
        skill_area="Programming Language",
        tech_stack="Python",
        evidence=[
            {
                "evidence_id": "evidence-a",
                "source": "source-a",
                "text": f"样例 {index}：使用 FastAPI 依赖注入开发接口",
            },
            {
                "evidence_id": "evidence-b",
                "source": "source-b",
                "text": f"样例 {index}：掌握 FastAPI 异步接口和依赖管理",
            },
        ],
    )


async def run(args: argparse.Namespace) -> dict:
    sys.path.insert(0, str(BACKEND))
    from app.providers import DeepSeekProvider
    import app.providers.llm as llm_module

    original_async_client = None
    if args.live:
        provider = DeepSeekProvider()
        if not provider.enabled:
            raise RuntimeError("--live requires DEEPSEEK_API_KEY")
    else:
        # Exercise the production provider's real classification, backoff and
        # bounded-attempt loop; only the HTTP transport is deterministic.
        transport = RecoverableFailureTransport(llm_module.httpx, args.fail_every)
        original_async_client = llm_module.httpx.AsyncClient
        llm_module.httpx.AsyncClient = transport.client_type()
        provider = DeepSeekProvider()
        provider.api_key = "offline-simulation-key"
        provider.base_url = "https://offline.test"
    agent = SkillGraphCompletionAgent(
        provider,
        timeout_seconds=args.timeout,
        max_attempts=args.max_attempts,
    )
    semaphore = asyncio.Semaphore(args.concurrency)

    async def one(index: int) -> dict:
        async with semaphore:
            started = time.perf_counter()
            diagnostics: dict = {}
            request = _request(index)
            try:
                output = await agent.complete(request, diagnostics=diagnostics)
                quality = evaluate_l45_output(request, output)
                return {
                    "ok": True,
                    "quality": quality.passed,
                    "issues": quality.issue_codes,
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "retry_count": int(diagnostics.get("retry_count") or 0),
                    "error_code": None,
                }
            except Exception as exc:
                return {
                    "ok": False,
                    "quality": False,
                    "issues": [],
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "retry_count": int(diagnostics.get("retry_count") or 0),
                    "error_code": diagnostics.get("error_code") or type(exc).__name__,
                }

    try:
        rows = await asyncio.gather(*(one(index) for index in range(args.runs)))
    finally:
        if original_async_client is not None:
            llm_module.httpx.AsyncClient = original_async_client
    latencies = sorted(row["latency_ms"] for row in rows)
    successes = sum(row["ok"] for row in rows)
    quality_passes = sum(row["quality"] for row in rows)
    report = {
        "mode": "live" if args.live else "simulation",
        "runs": args.runs,
        "concurrency": args.concurrency,
        "success_rate": round(successes / args.runs, 4),
        "quality_pass_rate": round(quality_passes / args.runs, 4),
        "retried_runs": sum(row["retry_count"] > 0 for row in rows),
        "total_retries": sum(row["retry_count"] for row in rows),
        "latency_ms": {
            "average": round(sum(latencies) / len(latencies), 2),
            "p95": nearest_rank_percentile(latencies, .95),
            "maximum": latencies[-1],
        },
        "error_codes": dict(Counter(row["error_code"] for row in rows if row["error_code"])),
        "quality_issues": dict(Counter(issue for row in rows for issue in row["issues"])),
    }
    report["accepted"] = (
        report["success_rate"] >= args.min_success_rate
        and report["quality_pass_rate"] >= args.min_quality_rate
        and report["latency_ms"]["p95"] <= args.max_p95_ms
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--fail-every", type=int, default=5)
    parser.add_argument("--min-success-rate", type=float, default=.98)
    parser.add_argument("--min-quality-rate", type=float, default=.95)
    parser.add_argument("--max-p95-ms", type=int, default=120000)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 1 or args.concurrency < 1:
        parser.error("--runs and --concurrency must be positive")
    report = asyncio.run(run(args))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
