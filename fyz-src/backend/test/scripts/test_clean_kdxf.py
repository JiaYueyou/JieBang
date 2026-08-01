"""科大讯飞离线清洗脚本的权威技能词典兼容测试。"""

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[4] / "scripts" / "clean_kdxf.py"
SPEC = importlib.util.spec_from_file_location("clean_kdxf", SCRIPT_PATH)
clean_kdxf = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(clean_kdxf)


def test_aliases_emit_canonical_skill_names():
    skills = clean_kdxf._extract_skills_from_text("熟悉 js、k8s 和 postgres")

    assert "JavaScript" in skills["编程语言"]
    assert "Kubernetes" in skills["DevOps/云工具"]
    assert "PostgreSQL" in skills["数据库"]
    assert "js" not in skills["编程语言"]


def test_display_categories_preserve_pipeline_semantics():
    skills = clean_kdxf._extract_skills_from_text(
        "使用 PyTorch、RabbitMQ、Hadoop，并参与物联网项目",
    )

    assert skills["AI/ML框架"] == ["PyTorch"]
    assert skills["中间件/消息队列"] == ["RabbitMQ"]
    assert skills["大数据技术"] == ["Hadoop"]
    assert skills["硬件/嵌入式"] == ["物联网"]


def test_specific_skill_does_not_emit_broader_overlapping_name():
    skills = clean_kdxf._extract_skills_from_text("C++ 与 Spring Boot")

    assert "C++" in skills["编程语言"]
    assert "C" not in skills["编程语言"]
    assert "Spring Boot" in skills["后端框架"]
    assert "Spring" not in skills["后端框架"]
