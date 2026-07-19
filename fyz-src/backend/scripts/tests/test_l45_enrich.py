"""Tests for L4-L5 enrichment agent."""

import sys
import os
from pathlib import Path

# Add agent-development to path
AGENT_DIR = Path(__file__).resolve().parents[3] / "agent-development"
sys.path.insert(0, str(AGENT_DIR))

from l45_agent.schema import AgentInput, SkillEvidence, AgentOutput, L4TechPoint, L5KnowledgePoint
from l45_agent.verify import L45Validator


def test_schema_creation():
    """Test that data models can be created."""
    evidence = SkillEvidence(
        source_doc_id=1,
        source_platform="智联招聘",
        evidence_text="精通Java和Spring Boot开发",
    )
    assert evidence.source_doc_id == 1
    assert "智联" in evidence.source_platform

    pt = L4TechPoint(
        name="Spring框架开发",
        detail="使用Spring Boot进行微服务开发",
        confidence=0.85,
    )
    assert pt.name == "Spring框架开发"
    assert pt.confidence == 0.85

    kp = L5KnowledgePoint(
        name="依赖注入",
        description="理解Spring IoC容器",
        difficulty="medium",
        confidence=0.8,
    )
    assert kp.difficulty == "medium"
    print("  PASS: schema_creation")


def test_agent_input():
    """Test AgentInput creation with evidence."""
    input_data = AgentInput(
        skill_name="MySQL",
        skill_area="database",
        job_directions=["后端开发工程师"],
        evidence=[
            SkillEvidence(
                source_doc_id=1,
                source_platform="智联招聘",
                evidence_text="精通MySQL数据库设计和优化",
            ),
            SkillEvidence(
                source_doc_id=2,
                source_platform="科大讯飞",
                evidence_text="熟悉MySQL索引优化和SQL调优",
            ),
        ],
    )
    assert input_data.skill_name == "MySQL"
    assert len(input_data.evidence) == 2
    print("  PASS: agent_input")


def test_validator_all_good():
    """Test validator passes high-confidence results."""
    output = AgentOutput(
        skill_name="MySQL",
        tech_points=[
            L4TechPoint(
                name="索引优化",
                detail="SQL索引设计",
                confidence=0.85,
                knowledge_points=[
                    L5KnowledgePoint(
                        name="联合索引",
                        description="最左前缀原则",
                        difficulty="medium",
                        confidence=0.82,
                    ),
                ],
            ),
        ],
    )
    validator = L45Validator(min_confidence=0.75)
    result = validator.validate(output)
    assert result.passed is True
    assert len(result.tech_points) == 1
    print("  PASS: validator_all_good")


def test_validator_filter_low():
    """Test validator filters low-confidence results."""
    output = AgentOutput(
        skill_name="MySQL",
        tech_points=[
            L4TechPoint(
                name="索引优化",
                detail="SQL索引设计",
                confidence=0.50,  # below threshold
                knowledge_points=[
                    L5KnowledgePoint(
                        name="联合索引",
                        description="最左前缀原则",
                        difficulty="medium",
                        confidence=0.82,
                    ),
                ],
            ),
        ],
    )
    validator = L45Validator(min_confidence=0.75)
    result = validator.validate(output)
    assert result.passed is False
    assert len(result.tech_points) == 0
    print("  PASS: validator_filter_low")


def test_validator_empty():
    """Test validator handles empty input."""
    output = AgentOutput(skill_name="MySQL", tech_points=[])
    validator = L45Validator()
    result = validator.validate(output)
    assert result.passed is False
    print("  PASS: validator_empty")


def test_validator_mixed():
    """Test validator keeps good points, discards bad ones."""
    output = AgentOutput(
        skill_name="Redis",
        tech_points=[
            L4TechPoint(
                name="缓存策略",
                detail="缓存设计",
                confidence=0.90,
                knowledge_points=[
                    L5KnowledgePoint(
                        name="过期策略",
                        description="TTL设置",
                        difficulty="easy",
                        confidence=0.88,
                    ),
                ],
            ),
            L4TechPoint(
                name="集群部署",  # will be filtered: L5 confidence too low
                detail="Redis集群",
                confidence=0.80,
                knowledge_points=[
                    L5KnowledgePoint(
                        name="分片",
                        description="数据分片",
                        difficulty="hard",
                        confidence=0.40,
                    ),
                ],
            ),
        ],
    )
    validator = L45Validator(min_confidence=0.75)
    result = validator.validate(output)
    assert result.passed is True
    assert len(result.tech_points) == 1
    assert result.tech_points[0].name == "缓存策略"
    print("  PASS: validator_mixed")


def test_proficiency_label():
    """Test proficiency label mapping."""
    from l45_agent.verify import _proficiency_label
    assert _proficiency_label(0.95) == "master"
    assert _proficiency_label(0.85) == "expert"
    assert _proficiency_label(0.70) == "skilled"
    assert _proficiency_label(0.55) == "familiar"
    assert _proficiency_label(0.30) == "basic"
    print("  PASS: proficiency_label")


if __name__ == "__main__":
    print("Testing L4-L5 Agent...")
    test_schema_creation()
    test_agent_input()
    test_validator_all_good()
    test_validator_filter_low()
    test_validator_empty()
    test_validator_mixed()
    test_proficiency_label()
    print("\nAll tests passed!")
