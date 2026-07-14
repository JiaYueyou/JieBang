"""
简历相关 Schema —— 简历的创建、更新、查看。
"""
from pydantic import BaseModel, Field


class PersonalInfoSchema(BaseModel):
    """个人信息"""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    avatar: str | None = None


class JobIntentSchema(BaseModel):
    """求职意向"""
    desired_position: str = ""
    desired_city: str = ""
    salary_expectation: str = ""
    work_mode: str = "fulltime"  # fulltime / intern / remote


class EducationSchema(BaseModel):
    """教育经历"""
    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: str = ""
    end_date: str = ""


class WorkExperienceSchema(BaseModel):
    """工作经历"""
    company: str = ""
    position: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    skills: list[str] = []


class ProjectSchema(BaseModel):
    """项目经历"""
    name: str = ""
    role: str = ""
    description: str = ""
    technologies: list[str] = []
    highlights: list[str] = []


class ResumeCreate(BaseModel):
    """创建简历请求"""
    name: str = Field(..., min_length=1, max_length=100, description="简历别名")
    target_position: str | None = None


class ResumeUpdate(BaseModel):
    """更新简历请求（所有字段可选）"""
    name: str | None = None
    target_position: str | None = None
    personal_info: PersonalInfoSchema | None = None
    job_intent: JobIntentSchema | None = None
    education: list[EducationSchema] | None = None
    work_experience: list[WorkExperienceSchema] | None = None
    projects: list[ProjectSchema] | None = None
    skills: list[dict] | None = None
    self_evaluation: str | None = None


class ResumeResponse(BaseModel):
    """简历详情响应"""
    id: int
    name: str
    target_position: str | None = None
    personal_info: PersonalInfoSchema = PersonalInfoSchema()
    job_intent: JobIntentSchema = JobIntentSchema()
    education: list[EducationSchema] = []
    work_experience: list[WorkExperienceSchema] = []
    projects: list[ProjectSchema] = []
    skills: list[dict] = []
    self_evaluation: str = ""
    source_file: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ResumeUploadResponse(BaseModel):
    """上传简历解析后的响应"""
    resume: ResumeResponse
    # 解析分析结果
    extracted_skills: list[str] = []    # 提取到的技能名列表
    parse_accuracy: float = 0.0         # 解析准确率评估
