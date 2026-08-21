"""SQLAlchemy 模型注册入口。

新增模型后必须在此导入，确保 Alembic 和测试能够发现完整 metadata。
"""

from app.models.user import User
from app.models.job import JobPosting, JobPostingSkill, JobPostingVersion
from app.models.skill import (
    AgentRun,
    AsyncTask,
    ExternalJobIdentity,
    ExternalJobVersion,
    JobImportQuarantine,
    JobSkillFact,
    JobSourceObservation,
    RawJobRecord,
    JobDuplicateCluster,
    Skill,
    SourceDocument,
    SourceSnapshot,
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
from app.models.data_source import DataSource, PipelineRun
from app.models.analysis import (
    AnalysisBaselineSkill,
    AnalysisBaselineSnapshot,
    AnalysisInsightDecision,
)
from app.models.matching import MatchEvidence, MatchRecord, Resume, ResumeParseResult, ResumeSkill
from app.models.internal_transfer import (
    EnterpriseDepartment,
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
    "Skill", "SourceDocument", "SourceSnapshot", "ExternalJobIdentity", "ExternalJobVersion",
    "JobSourceObservation", "JobImportQuarantine", "RawJobRecord", "SourceTrustPolicy", "JobSkillFact",
    "AgentRun", "AsyncTask", "StandardJob", "StandardJobAlias", "StandardJobSource",
    "JobDuplicateCluster",
    "GraphSnapshot", "GraphSyncBatch", "GraphEnrichmentCandidate",
    "DataSource", "PipelineRun",
    "AnalysisInsightDecision", "AnalysisBaselineSnapshot", "AnalysisBaselineSkill",
    "Resume", "ResumeParseResult", "ResumeSkill", "MatchRecord", "MatchEvidence",
    "EnterpriseDepartment", "EnterpriseEmployeeDirectory", "EnterpriseTalent", "InternalPosition", "TransferRuleSet", "TransferDecision",
    "UserFavorite", "UserBrowseHistory",
    "EvidenceChunk", "RetrievalIndexVersion", "RetrievalIndexEntry",
    "RetrievalQueryLog", "AgentClaimCitation",
]
