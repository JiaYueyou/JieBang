"""后端加载仓库内独立 Agent 包的唯一适配接口。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_agent_runtime_path() -> Path:
    configured = os.getenv("JIEBANG_AGENT_PATH")
    source_dir = (
        Path(configured).expanduser().resolve()
        if configured
        else Path(__file__).resolve().parents[4] / "agent-development" / "src"
    )
    if not (source_dir / "jiebang_agents" / "__init__.py").is_file():
        raise RuntimeError(f"Agent runtime package not found: {source_dir}")
    source_text = str(source_dir)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    return source_dir


ensure_agent_runtime_path()

from jiebang_agents import JDGenerationAgent  # noqa: E402
from jiebang_agents.career_planning import (  # noqa: E402
    CareerAnalysisOutput,
    CareerAnalysisRequest,
    CareerPlanCandidate,
    CareerPlanningAgent,
    CareerRecommendation,
    LearningStep,
    ResumeProfile,
)
from jiebang_agents.jd_generation import (  # noqa: E402
    GenerateJDRequest,
    GeneratedJDDraft,
    JDGenerationMode,
    LLMGeneratedJDDraft,
)
from jiebang_agents.graph_enrichment import (  # noqa: E402
    GraphEnrichmentAgent,
    GraphEnrichmentOutput,
    GraphEvidenceInput,
    KnowledgePointOutput,
    SkillGraphCompletionAgent,
    SkillGraphCompletionInput,
    TechPointOutput,
)
from jiebang_agents.skill_extraction import (  # noqa: E402
    LLMDiscoveredSkill,
    LLMDiscoveredSkills,
    SkillExtractionAgent,
)
from jiebang_agents.match_explanation import (  # noqa: E402
    MatchEvidenceInput, MatchExplanationAgent, MatchExplanationOutput, MatchExplanationRequest,
)

__all__ = [
    "ensure_agent_runtime_path",
    "JDGenerationAgent",
    "JDGenerationMode",
    "GenerateJDRequest",
    "GeneratedJDDraft",
    "LLMGeneratedJDDraft",
    "CareerPlanningAgent",
    "CareerAnalysisRequest",
    "CareerPlanCandidate",
    "CareerAnalysisOutput",
    "CareerRecommendation",
    "LearningStep",
    "ResumeProfile",
    "SkillExtractionAgent",
    "LLMDiscoveredSkill",
    "LLMDiscoveredSkills",
    "GraphEnrichmentAgent",
    "SkillGraphCompletionAgent",
    "SkillGraphCompletionInput",
    "GraphEvidenceInput",
    "GraphEnrichmentOutput",
    "KnowledgePointOutput",
    "TechPointOutput",
    "MatchExplanationAgent", "MatchExplanationRequest", "MatchExplanationOutput", "MatchEvidenceInput",
]
