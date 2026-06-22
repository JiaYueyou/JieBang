"""技能词典、归一化和规则抽取测试。"""

from app.domain.skill_dictionary import canonical_key, normalize_skill
from app.services.skill_extractor import RuleSkillExtractor, content_fingerprint


def test_alias_normalization():
    assert normalize_skill("K8s") == ("Kubernetes", "tool")
    assert normalize_skill("SpringBoot") == ("Spring Boot", "framework")
    assert normalize_skill("Postgres") == ("PostgreSQL", "database")
    assert normalize_skill("ES") == ("Elasticsearch", "database")
    assert normalize_skill("python") == ("Python", "programming_language")
    assert normalize_skill("JAVA") == ("Java", "programming_language")
    assert canonical_key("Spring Boot") == "springboot"
    assert {canonical_key("C"), canonical_key("C++"), canonical_key("C#")} == {
        "c", "cpp", "csharp"
    }


def test_rule_extraction_and_preferred_context():
    result = RuleSkillExtractor().extract(
        jd_text="精通 Java、Spring Boot 和 MySQL，有 Docker 或 K8s 经验者优先。"
    )
    by_name = {item.name: item for item in result.skills}
    assert {"Java", "Spring Boot", "MySQL", "Docker", "Kubernetes"} <= set(by_name)
    assert by_name["Java"].kind.value == "required"
    assert by_name["Kubernetes"].kind.value == "preferred"
    assert by_name["Kubernetes"].confidence >= 0.9


def test_content_fingerprint_is_stable_and_content_sensitive():
    row = {"source": "A", "url": "u", "title": "Java", "company": "C", "jd_text": "MySQL"}
    assert content_fingerprint(row) == content_fingerprint(dict(row))
    assert content_fingerprint(row) != content_fingerprint({**row, "jd_text": "Redis"})
