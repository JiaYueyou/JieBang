"""Verify configured OpenAI-compatible embeddings without printing secrets."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.retrieval import cosine_similarity
from app.providers.embedding import build_embedding_provider


async def verify() -> dict:
    provider = build_embedding_provider(provider_name="openai")
    vectors = await provider.embed_texts(
        [
            "Java 后端工程师需要关系型数据库设计和查询调优能力",
            "负责服务端数据库建模、SQL 查询与性能优化",
            "研究深海珊瑚的基因序列和生态演化",
        ]
    )
    return {
        "status": "ok",
        "provider": provider.name,
        "model": provider.model,
        "dimension": provider.dimension,
        "base_url": provider.base_url,
        "vector_count": len(vectors),
        "related_similarity": cosine_similarity(vectors[0], vectors[1]),
        "unrelated_similarity": cosine_similarity(vectors[0], vectors[2]),
    }


def main() -> int:
    try:
        report = asyncio.run(verify())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
