"""Read-only Phase 0 baseline collection for MySQL, Neo4j and Agent runs."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.neo4j import run_read
from app.core.time import utc_isoformat, utc_now
from app.domain.statuses import AgentRunStatus, TaskStatus, TrustStage
from app.models import (
    AgentRun,
    AsyncTask,
    GraphEnrichmentCandidate,
    GraphSnapshot,
    GraphSyncBatch,
    JobPosting,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
    StandardJob,
)
from app.repositories import Neo4jGraphRepository

COUNT_MODELS = {
    "job_posting": JobPosting,
    "source_document": SourceDocument,
    "raw_job_record": RawJobRecord,
    "skill": Skill,
    "job_skill_fact": JobSkillFact,
    "standard_job": StandardJob,
    "agent_run": AgentRun,
    "async_task": AsyncTask,
    "graph_snapshot": GraphSnapshot,
    "graph_sync_batch": GraphSyncBatch,
    "graph_enrichment_candidate": GraphEnrichmentCandidate,
}


async def _table_names(session: AsyncSession) -> set[str]:
    connection = await session.connection()
    names = await connection.run_sync(lambda sync_connection: inspect(sync_connection).get_table_names())
    return set(names)


async def _status_counts(
    session: AsyncSession, model: Any, column: Any
) -> dict[str, int]:
    rows = await session.execute(
        select(column, func.count()).select_from(model).group_by(column).order_by(column)
    )
    return {str(status): int(count) for status, count in rows}


async def collect_relational_baseline(session: AsyncSession) -> dict[str, Any]:
    tables = await _table_names(session)
    counts: dict[str, int | None] = {}
    for name, model in COUNT_MODELS.items():
        counts[name] = (
            int(await session.scalar(select(func.count()).select_from(model)) or 0)
            if name in tables
            else None
        )

    statuses: dict[str, dict[str, int]] = {}
    status_models = {
        "job_skill_fact": (JobSkillFact, JobSkillFact.verification_status),
        "agent_run": (AgentRun, AgentRun.status),
        "async_task": (AsyncTask, AsyncTask.status),
        "graph_snapshot": (GraphSnapshot, GraphSnapshot.status),
        "graph_sync_batch": (GraphSyncBatch, GraphSyncBatch.status),
        "graph_enrichment_candidate": (
            GraphEnrichmentCandidate,
            GraphEnrichmentCandidate.verification_status,
        ),
    }
    for name, (model, column) in status_models.items():
        statuses[name] = await _status_counts(session, model, column) if name in tables else {}

    agent_metrics: list[dict[str, Any]] = []
    if "agent_run" in tables:
        rows = await session.execute(
            select(
                AgentRun.agent_type,
                AgentRun.status,
                func.count(AgentRun.id),
                func.avg(AgentRun.duration_ms),
                func.max(AgentRun.duration_ms),
            )
            .group_by(AgentRun.agent_type, AgentRun.status)
            .order_by(AgentRun.agent_type, AgentRun.status)
        )
        agent_metrics = [
            {
                "agent_type": agent_type,
                "status": status,
                "count": int(count),
                "avg_duration_ms": round(float(avg_duration), 2) if avg_duration is not None else None,
                "max_duration_ms": int(max_duration) if max_duration is not None else None,
            }
            for agent_type, status, count, avg_duration, max_duration in rows
        ]

    latest_snapshot = None
    if "graph_snapshot" in tables:
        snapshot = await session.scalar(
            select(GraphSnapshot).order_by(GraphSnapshot.created_at.desc()).limit(1)
        )
        if snapshot is not None:
            latest_snapshot = {
                "id": snapshot.id,
                "version": snapshot.version,
                "status": snapshot.status,
                "node_count": snapshot.node_count,
                "edge_count": snapshot.edge_count,
                "fact_count": snapshot.fact_count,
                "created_at": utc_isoformat(snapshot.created_at),
                "completed_at": utc_isoformat(snapshot.completed_at),
            }

    alembic_revision = None
    if "alembic_version" in tables:
        alembic_revision = await session.scalar(text("SELECT version_num FROM alembic_version"))

    return {
        "connected": True,
        "dialect": session.bind.dialect.name if session.bind is not None else None,
        "alembic_revision": alembic_revision,
        "counts": counts,
        "statuses": statuses,
        "agent_metrics": agent_metrics,
        "latest_graph_snapshot": latest_snapshot,
    }


def _safe_neo4j_query(query: str) -> dict[str, Any]:
    try:
        return {"ok": True, "rows": run_read(query)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:1000], "rows": []}


def collect_neo4j_baseline() -> dict[str, Any]:
    health = _safe_neo4j_query("RETURN 1 AS ok")
    if not health["ok"]:
        return {
            "connected": False,
            "error": health["error"],
            "server": None,
            "counts": None,
            "vector": {"supported": False, "procedures": [], "functions": [], "probe_errors": []},
        }

    components = _safe_neo4j_query(
        "CALL dbms.components() YIELD name, versions, edition "
        "RETURN name, versions, edition"
    )
    procedures = _safe_neo4j_query(
        "SHOW PROCEDURES YIELD name "
        "WHERE name STARTS WITH 'db.index.vector' RETURN name ORDER BY name"
    )
    functions = _safe_neo4j_query(
        "SHOW FUNCTIONS YIELD name "
        "WHERE name STARTS WITH 'vector.' RETURN name ORDER BY name"
    )
    try:
        counts = Neo4jGraphRepository().counts()
    except Exception as exc:
        counts = {"error": f"{type(exc).__name__}: {exc}"[:1000]}

    procedure_names = [row["name"] for row in procedures["rows"] if "name" in row]
    function_names = [row["name"] for row in functions["rows"] if "name" in row]
    probe_errors = [
        probe["error"]
        for probe in (components, procedures, functions)
        if not probe["ok"]
    ]
    return {
        "connected": True,
        "server": components["rows"][0] if components["rows"] else None,
        "counts": counts,
        "vector": {
            "supported": bool(procedure_names or function_names),
            "procedures": procedure_names,
            "functions": function_names,
            "probe_errors": probe_errors,
        },
    }


def collect_git_metadata(project_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str | None:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    status = run("status", "--short")
    return {
        "head": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status),
        "changed_entry_count": len(status.splitlines()) if status else 0,
    }


def rag_decision(neo4j: dict[str, Any]) -> dict[str, Any]:
    vector_supported = bool(neo4j.get("connected") and neo4j.get("vector", {}).get("supported"))
    return {
        "authority": "MySQL stores source, evidence, review and publication metadata.",
        "index_role": "Vector indexes are derived, rebuildable retrieval read models.",
        "selected_phase1_backend": (
            "neo4j_vector_index_pilot"
            if vector_supported
            else "local_rebuildable_vector_index"
        ),
        "reason": (
            "The connected Neo4j server exposes vector procedures/functions."
            if vector_supported
            else "Neo4j vector capability was not confirmed; keep Phase 1 local-first and portable."
        ),
    }


def build_report(
    *,
    git: dict[str, Any],
    relational: dict[str, Any],
    neo4j: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "phase0-baseline-v1",
        "generated_at": utc_isoformat(utc_now()),
        "git": git,
        "contracts": {
            "task_statuses": [item.value for item in TaskStatus],
            "agent_run_statuses": [item.value for item in AgentRunStatus],
            "trust_stages": [item.value for item in TrustStage],
            "timestamp_api": "UTC RFC3339 with Z suffix",
            "timestamp_database_phase0": "Existing naive DateTime columns receive UTC-naive compatibility values.",
        },
        "relational": relational,
        "neo4j": neo4j,
        "rag_decision": rag_decision(neo4j),
    }


def render_markdown(report: dict[str, Any]) -> str:
    relational = report["relational"]
    neo4j = report["neo4j"]
    decision = report["rag_decision"]
    lines = [
        "# FYZ Phase 0 基线报告",
        "",
        f"- 生成时间：`{report['generated_at']}`",
        f"- Git HEAD：`{report['git'].get('head')}`",
        f"- 分支：`{report['git'].get('branch')}`",
        f"- 工作区变更条目：`{report['git'].get('changed_entry_count')}`",
        f"- 数据库方言：`{relational.get('dialect')}`",
        f"- Alembic revision：`{relational.get('alembic_revision')}`",
        f"- Neo4j 连通：`{neo4j.get('connected')}`",
        f"- Neo4j 服务信息：`{neo4j.get('server')}`",
        f"- Neo4j 图计数：`{neo4j.get('counts')}`",
        f"- Neo4j 向量能力：`{neo4j.get('vector')}`",
        "",
        "## MySQL/关系库计数",
        "",
    ]
    lines.extend(f"- `{name}`：`{count}`" for name, count in relational["counts"].items())
    lines.extend(
        [
            "",
            "## 状态分布",
            "",
        ]
    )
    lines.extend(
        f"- `{name}`：`{counts}`" for name, counts in relational["statuses"].items()
    )
    lines.extend(
        [
            "",
            "## Agent耗时",
            "",
            f"`{relational['agent_metrics']}`",
            "",
            "## RAG索引决策",
            "",
            f"- 权威数据：{decision['authority']}",
            f"- 索引角色：{decision['index_role']}",
            f"- Phase 1 默认后端：`{decision['selected_phase1_backend']}`",
            f"- 原因：{decision['reason']}",
            "",
        ]
    )
    return "\n".join(lines)
