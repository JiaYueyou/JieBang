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
    JobDuplicateCluster,
    Skill,
    SourceDocument,
    SourceTrustPolicy,
)
from app.models.graph import (
    GraphEnrichmentCandidate,
    GraphSnapshot,
    GraphSyncBatch,
    StandardJob,
    StandardJobAlias,
    StandardJobSource,
)
from app.models.data_source import DataSource
from app.models.analysis import AnalysisInsightDecision
from app.models.matching import MatchEvidence, MatchRecord, Resume, ResumeParseResult, ResumeSkill
from app.models.internal_transfer import (
    EnterpriseEmployeeDirectory,
    EnterpriseTalent,
    InternalPosition,
    TransferDecision,
    TransferRuleSet,
)
from app.models.user_activity import UserBrowseHistory, UserFavorite
from app.models.retrieval import (
    AgentClaimCitation,
    EvidenceChunk,
    RetrievalIndexEntry,
    RetrievalIndexVersion,
    RetrievalQueryLog,
)

__all__ = [
    "User", "JobPosting", "JobPostingSkill", "JobPostingVersion",
    "Skill", "SourceDocument", "RawJobRecord", "SourceTrustPolicy", "JobSkillFact",
    "AgentRun", "AsyncTask", "StandardJob", "StandardJobAlias", "StandardJobSource",
    "JobDuplicateCluster",
    "GraphSnapshot", "GraphSyncBatch", "GraphEnrichmentCandidate",
    "DataSource",
    "AnalysisInsightDecision",
    "Resume", "ResumeParseResult", "ResumeSkill", "MatchRecord", "MatchEvidence",
    "EnterpriseEmployeeDirectory", "EnterpriseTalent", "InternalPosition", "TransferRuleSet", "TransferDecision",
    "UserFavorite", "UserBrowseHistory",
    "EvidenceChunk", "RetrievalIndexVersion", "RetrievalIndexEntry",
    "RetrievalQueryLog", "AgentClaimCitation",
]
