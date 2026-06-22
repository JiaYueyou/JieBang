"""岗位管理请求与响应 Schema。"""

from datetime import datetime
from enum import Enum
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _parse_salary_fields(value):
    if not isinstance(value, dict) or value.get("salary_min") is not None:
        return value
    text = value.get("salary_range")
    if not isinstance(text, str):
        return value
    numbers = re.findall(r"(\d+(?:\.\d+)?)\s*[kK]", text)
    if len(numbers) < 2:
        return value
    parsed = dict(value)
    parsed["salary_min"] = int(float(numbers[0]) * 1000)
    parsed["salary_max"] = int(float(numbers[1]) * 1000)
    months = re.search(r"(\d+)\s*薪", text)
    if months:
        parsed["salary_months"] = int(months.group(1))
    return parsed


class JobStatus(str, Enum):
    draft = "draft"
    open = "open"
    paused = "paused"
    closed = "closed"


class JobWriteBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=120)
    standardized_title: str | None = Field(default=None, max_length=120)
    level: str = Field(default="mid", min_length=1, max_length=30)
    department: str = Field(min_length=1, max_length=100)
    company: str | None = Field(default=None, max_length=150)
    location: str | None = Field(default=None, max_length=100)
    experience: str | None = Field(default=None, max_length=50)
    education: str | None = Field(default=None, max_length=50)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_months: int = Field(default=12, ge=1, le=24)
    salary_range: str | None = None
    headcount: int = Field(default=1, ge=1, le=10000)
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    bonus_skills: list[str] = Field(default_factory=list)
    jd_text: str = ""
    status: JobStatus = JobStatus.draft
    urgent: bool = False

    @model_validator(mode="before")
    @classmethod
    def parse_salary_range(cls, value):
        return _parse_salary_fields(value)

    @model_validator(mode="after")
    def validate_salary(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobCreate(JobWriteBase):
    pass


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, min_length=1, max_length=120)
    standardized_title: str | None = Field(default=None, max_length=120)
    level: str | None = Field(default=None, min_length=1, max_length=30)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    company: str | None = Field(default=None, max_length=150)
    location: str | None = Field(default=None, max_length=100)
    experience: str | None = Field(default=None, max_length=50)
    education: str | None = Field(default=None, max_length=50)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_months: int | None = Field(default=None, ge=1, le=24)
    salary_range: str | None = None
    headcount: int | None = Field(default=None, ge=1, le=10000)
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    skills: list[str] | None = None
    bonus_skills: list[str] | None = None
    jd_text: str | None = None
    status: JobStatus | None = None
    urgent: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_salary_range(cls, value):
        return _parse_salary_fields(value)

    @model_validator(mode="after")
    def validate_salary(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min cannot exceed salary_max")
        return self


class JobStatusUpdate(BaseModel):
    status: JobStatus


class JobSummary(BaseModel):
    id: int
    title: str
    standardized_title: str | None
    level: str
    department: str
    company: str | None
    location: str | None
    experience: str | None
    education: str | None
    salary_min: int | None
    salary_max: int | None
    salary_months: int
    salary_range: str
    headcount: int
    responsibilities: list[str]
    requirements: list[str]
    skills: list[str]
    bonus_skills: list[str]
    jd_text: str
    status: JobStatus
    urgent: bool
    created_at: datetime
    updated_at: datetime


class JobVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    version_no: int
    snapshot: dict
    change_reason: str
    created_by: int
    created_at: datetime
