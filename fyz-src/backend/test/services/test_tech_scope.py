import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from spider_framework.tech_scope import classify_tech_scope


def test_keeps_ai_software_and_hardware_roles():
    samples = [
        {"title": "服务端开发工程师"},
        {"title": "LongCat - 基座大模型评测分析算法研究员"},
        {"title": "FPGA逻辑开发工程师"},
        {"title": "AI 产品运营（体验与服务方向）"},
    ]

    assert all(classify_tech_scope(**sample).in_scope for sample in samples)


def test_excludes_non_technical_business_roles():
    samples = [
        {"title": "销售运营-销售策略"},
        {"title": "HR 团队"},
        {"title": "酒店运营经理"},
        {"title": "景点游玩高级产品专家", "description": "负责交易转化和收入增长"},
    ]

    assert all(not classify_tech_scope(**sample).in_scope for sample in samples)


def test_category_or_dense_jd_can_supply_scope_evidence():
    category = classify_tech_scope(title="解决方案架构顾问", category="技术类")
    description = classify_tech_scope(
        title="专项人才",
        description="使用 Python、Linux 和 Kubernetes 构建分布式平台",
    )

    assert category.in_scope
    assert category.reason == "technical_title"
    assert description.in_scope
    assert description.reason == "technical_description"
