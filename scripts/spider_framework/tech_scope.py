"""Shared scope filter for internet, AI, software, and hardware job crawlers.

The filter is intentionally conservative.  A job must expose an explicit
technical signal in its title/category, or several technical signals in its
description.  This keeps sales, HR, finance, retail, and logistics roles out of
the trend baseline while retaining AI product and infrastructure roles.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


STRONG_TITLE_TERMS = (
    "AI", "AIGC", "Agent", "LLM", "大模型", "机器学习", "深度学习", "算法",
    "研发", "开发", "工程师", "架构", "前端", "后端", "服务端", "客户端",
    "全栈", "软件", "硬件", "嵌入式", "芯片", "半导体", "IC", "FPGA",
    "GPU", "编译器", "数据库", "数据工程", "数据科学", "数据分析", "测试开发",
    "SRE", "DevOps", "运维", "安全", "网络", "云计算", "平台", "机器人",
)

TECH_CATEGORY_TERMS = (
    "技术", "研发", "算法", "人工智能", "AI", "软件", "硬件", "芯片",
    "半导体", "数据", "计算机", "全栈", "核心系统", "深度学习", "模型",
    "运维", "产品",
)

DESCRIPTION_TERMS = (
    "Python", "Java", "C++", "Go", "Rust", "JavaScript", "TypeScript",
    "Linux", "SQL", "NoSQL", "Redis", "Kafka", "Spark", "Flink", "Docker",
    "Kubernetes", "微服务", "分布式", "云原生", "大模型", "机器学习", "深度学习",
    "神经网络", "推荐系统", "搜索算法", "计算机视觉", "自然语言处理", "RAG",
    "Agent", "GPU", "CUDA", "芯片", "电路", "FPGA", "嵌入式", "操作系统",
)

BUSINESS_TITLE_TERMS = (
    "人力", "HR", "招聘", "财务", "法务", "行政", "采购", "销售", "客服",
    "商务", "公关", "市场营销", "门店", "骑手", "司机", "仓储", "物流",
    "供应链", "酒店运营", "商家运营", "招商", "区域运营",
)

PRODUCT_TERMS = ("产品经理", "产品专家", "产品负责人", "产品策划")
PRODUCT_TECH_TERMS = (
    "AI", "大模型", "Agent", "数据", "平台", "系统", "SaaS", "云", "开发者",
    "搜索", "推荐", "安全", "基础设施", "软件", "硬件",
)


@dataclass(frozen=True)
class TechScopeDecision:
    in_scope: bool
    reason: str
    matched_terms: tuple[str, ...]


def _matches(text: str, terms: Iterable[str]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


def classify_tech_scope(
    *,
    title: str,
    category: str | None = None,
    department: str | None = None,
    description: str | None = None,
) -> TechScopeDecision:
    """Classify one public job record against the project's collection scope."""

    title_text = re.sub(r"\s+", " ", title or "").strip()
    category_text = " ".join(value for value in (category, department) if value)
    description_text = description or ""
    title_matches = _matches(title_text, STRONG_TITLE_TERMS)
    category_matches = _matches(category_text, TECH_CATEGORY_TERMS)
    description_matches = _matches(description_text, DESCRIPTION_TERMS)
    business_matches = _matches(title_text, BUSINESS_TITLE_TERMS)

    # Explicit AI/engineering signals win over generic business wording.  This
    # retains roles such as "AI 产品运营" but excludes "销售运营".
    if title_matches:
        return TechScopeDecision(True, "technical_title", tuple(title_matches))

    if any(term in title_text for term in PRODUCT_TERMS):
        product_matches = _matches(
            f"{title_text} {category_text} {description_text}",
            PRODUCT_TECH_TERMS,
        )
        if product_matches:
            return TechScopeDecision(True, "technical_product", tuple(product_matches))
        return TechScopeDecision(False, "non_technical_product", ())

    if business_matches:
        return TechScopeDecision(False, "business_title", tuple(business_matches))

    if category_matches:
        return TechScopeDecision(True, "technical_category", tuple(category_matches))

    unique_description_matches = tuple(dict.fromkeys(description_matches))
    if len(unique_description_matches) >= 3:
        return TechScopeDecision(True, "technical_description", unique_description_matches)

    return TechScopeDecision(False, "insufficient_technical_evidence", unique_description_matches)


def is_in_scope_job(**kwargs: str | None) -> bool:
    return classify_tech_scope(**kwargs).in_scope
