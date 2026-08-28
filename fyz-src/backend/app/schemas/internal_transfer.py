"""企业内部转岗 API 契约。"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InternalPositionStatus(str, Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    open = "open"
    paused = "paused"
    filled = "filled"
    closed = "closed"


class EnterpriseTalentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=1, max_length=100)
    current_position: str = Field(min_length=1, max_length=120)
    level: str = Field(default="mid", min_length=1, max_length=30)
    location: str | None = Field(default=None, max_length=100)
    tenure_months: int = Field(default=0, ge=0, le=720)
    position_tenure_months: int = Field(default=0, ge=0, le=720)
    skills: list[str] = Field(default_factory=list, max_length=50)
    project_highlights: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default="active", pattern="^(active|inactive|restricted)$")


class EnterpriseTalentSummary(EnterpriseTalentCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class EnterpriseDepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    manager: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)
    status: str = Field(default="active", pattern="^(active|inactive)$")


class EnterpriseDepartmentSummary(EnterpriseDepartmentCreate):
    id: int
    employee_count: int = 0
    created_at: datetime
    updated_at: datetime


class EmployeeDirectoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_no: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=1, max_length=100)
    current_position: str = Field(min_length=1, max_length=120)
    level: str = Field(default="mid", min_length=1, max_length=30)
    location: str | None = Field(default=None, max_length=100)
    tenure_months: int = Field(default=0, ge=0, le=720)
    position_tenure_months: int = Field(default=0, ge=0, le=720)
    skills: list[str] = Field(default_factory=list, max_length=50)
    project_highlights: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default="active", pattern="^(active|inactive)$")
    source: str = Field(default="hr_sync", max_length=40)


class EmployeeDirectorySummary(EmployeeDirectoryCreate):
    id: int
    in_talent_pool: bool
    synced_at: datetime


class InternalPositionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    standardized_title: str | None = Field(default=None, max_length=120)
    department: str = Field(min_length=1, max_length=100)
    receiving_manager: str | None = Field(default=None, max_length=100)
    level: str = Field(default="mid", min_length=1, max_length=30)
    headcount: int = Field(default=1, ge=1, le=10000)
    open_reason: str = Field(default="组织人才配置", max_length=300)
    responsibilities: list[str] = Field(default_factory=list, max_length=20)
    requirements: list[str] = Field(default_factory=list, max_length=20)
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    trainable_skills: list[str] = Field(default_factory=list, max_length=30)
    transfer_profile: list[str] = Field(default_factory=list, max_length=20)
    manager_confirmations: list[str] = Field(default_factory=list, max_length=20)
    min_tenure_months: int = Field(default=0, ge=0, le=720)
    min_position_tenure_months: int = Field(default=0, ge=0, le=720)
    allowed_departments: list[str] = Field(default_factory=list, max_length=50)
    restrictions: list[str] = Field(default_factory=list, max_length=20)
    target_start_date: date | None = None
    open_from: date | None = None
    open_until: date | None = None
    internal_description: str = Field(default="", max_length=12000)
    status: InternalPositionStatus = InternalPositionStatus.draft

    @model_validator(mode="after")
    def validate_internal_position(self):
        if self.open_from and self.open_until and self.open_from > self.open_until:
            raise ValueError("open_from must be before or equal to open_until")
        required = {item.strip().casefold() for item in self.required_skills if item.strip()}
        trainable = {item.strip().casefold() for item in self.trainable_skills if item.strip()}
        if required & trainable:
            raise ValueError("required_skills and trainable_skills must not overlap")
        return self


class InternalPositionSummary(InternalPositionCreate):
    id: int
    created_at: datetime
    updated_at: datetime


class InternalPositionStatusUpdate(BaseModel):
    status: InternalPositionStatus


class TransferRuleSetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    min_tenure_months: int = Field(default=0, ge=0, le=720)
    min_position_tenure_months: int = Field(default=0, ge=0, le=720)
    min_match_score: int = Field(default=60, ge=0, le=100)
    skill_weight: int = Field(default=85, ge=0, le=100)
    tenure_weight: int = Field(default=15, ge=0, le=100)
    status: str = Field(default="active", pattern="^(draft|active|inactive)$")

    @model_validator(mode="after")
    def weights_total_one_hundred(self):
        if self.skill_weight + self.tenure_weight != 100:
            raise ValueError("skill_weight and tenure_weight must total 100")
        return self


class TransferRuleSetUpdate(TransferRuleSetCreate):
    """修改已有规则；版本号保持不变，便于审计规则生命周期。"""


class TransferRuleSetSummary(TransferRuleSetCreate):
    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class ResumeAdmissionRequest(BaseModel):
    """将外部候选人正式录用为企业员工并加入人才池。"""

    model_config = ConfigDict(extra="forbid")
    department: str = Field(min_length=1, max_length=100)
    current_position: str = Field(min_length=1, max_length=120)
    level: str = Field(default="junior", min_length=1, max_length=30)
    location: str | None = Field(default=None, max_length=100)


class MatchByTalentRequest(BaseModel):
    talent_id: int
    position_ids: list[int] = Field(default_factory=list, max_length=100)
    rule_set_id: int | None = None


class MatchByPositionRequest(BaseModel):
    position_id: int
    talent_ids: list[int] = Field(default_factory=list, max_length=500)
    rule_set_id: int | None = None


class InternalMatchResult(BaseModel):
    talent_id: int
    employee_no: str
    talent_name: str
    current_department: str
    current_position: str
    position_id: int
    position_title: str
    target_department: str
    eligible: bool
    disqualifications: list[str]
    score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    trainable_gaps: list[str]
    estimated_development_weeks: int
    rule_set_id: int | None
    rule_version: int


class SkillDemandSummary(BaseModel):
    skill: str
    position_count: int
    demand_headcount: int
    talent_supply: int
    gap: int
    departments: list[str]
    requirement_type: str


class TransferDecisionCreate(BaseModel):
    talent_id: int
    position_id: int
    rule_set_id: int | None = None
    note: str = Field(default="", max_length=2000)


class TransferDecisionSummary(BaseModel):
    id: int
    talent_id: int
    talent_name: str
    position_id: int
    position_title: str
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    status: str
    note: str
    created_at: datetime
