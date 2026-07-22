"""
爬虫招聘数据模型 —— jie_bang.raw_job_record 只读映射。
"""
from dataclasses import dataclass


@dataclass
class RawJobRecord:
    """raw_job_record 表字段映射（只读）"""
    id: int
    source_document_id: str | None
    title: str | None
    standardized_title: str | None
    company: str | None
    city: str | None
    salary_text: str | None
    experience_text: str | None
    education_text: str | None
    jd_text: str | None
    responsibilities: str | None
    requirements: str | None
    keywords: str | None  # 逗号分隔，如 "python,java,mysql"
    posted_at_text: str | None
    crawled_at_text: str | None
    dedup_status: str | None
    normalized_data: dict | None  # JSON
    created_at: str | None
