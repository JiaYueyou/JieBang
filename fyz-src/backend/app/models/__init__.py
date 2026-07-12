"""SQLAlchemy 模型注册入口。

新增模型后必须在此导入，确保 Alembic 和测试能够发现完整 metadata。
"""

from app.models.user import User
from app.models.job import JobPosting, JobPostingSkill, JobPostingVersion
from app.models.skill import (
    AgentRun,
    AsyncTask,
    JobSkillFact,
    RawJobRecord,
    Skill,
    SourceDocument,
)
from app.models.graph import (
    GraphEnrichmentCandidate,
    GraphSnapshot,
    GraphSyncBatch,
    StandardJob,
    StandardJobSource,
)
from app.models.analysis import AnalysisInsightDecision
from app.models.matching import MatchEvidence, MatchRecord, Resume, ResumeParseResult, ResumeSkill

__all__ = [
    "User", "JobPosting", "JobPostingSkill", "JobPostingVersion",
    "Skill", "SourceDocument", "RawJobRecord", "JobSkillFact",
    "AgentRun", "AsyncTask", "StandardJob", "StandardJobSource",
    "GraphSnapshot", "GraphSyncBatch", "GraphEnrichmentCandidate",
    "AnalysisInsightDecision",
    "Resume", "ResumeParseResult", "ResumeSkill", "MatchRecord", "MatchEvidence",
]
