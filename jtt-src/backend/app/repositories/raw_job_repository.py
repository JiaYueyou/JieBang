"""
爬虫招聘数据仓库 —— 查询 jie_bang.raw_job_record（只读），关联 standard_job 获取分类。
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RawJobRepository:
    """爬虫招聘数据访问层（只读，raw SQL）"""

    # 基础 JOIN 片段
    BASE_JOIN = """
        FROM raw_job_record r
        JOIN source_document sd ON r.source_document_id = sd.id
        JOIN standard_job_source sjs ON sjs.source_id = sd.id AND sjs.source_type = 'raw'
        JOIN standard_job sj ON sj.id = sjs.standard_job_id
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_jobs(
        self, category: str | None = None, keyword: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """分页查询爬虫岗位，支持分类（stack→category）和关键词搜索"""
        conditions: list[str] = []
        params: dict = {}

        if category == "new":
            conditions.append("sj.stack = 'ai'")
        elif category == "existing":
            conditions.append("sj.stack IN ('backend', 'data', 'devops')")

        if keyword:
            conditions.append(
                "(r.standardized_title LIKE :kw OR r.jd_text LIKE :kw OR r.keywords LIKE :kw)"
            )
            params["kw"] = f"%{keyword}%"

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # 计数
        count_sql = text(f"SELECT COUNT(*) as cnt {self.BASE_JOIN} {where_clause}")
        count_result = await self.db.execute(count_sql, params)
        total = (count_result.scalar()) or 0

        # 分页查询
        offset = (page - 1) * page_size
        select_fields = """
            SELECT r.id, r.standardized_title, r.company, r.city,
                   r.salary_text, r.experience_text, r.education_text,
                   r.jd_text, r.responsibilities, r.requirements,
                   r.keywords, r.posted_at_text, r.crawled_at_text,
                   sj.stack
        """
        query_sql = text(
            f"{select_fields} {self.BASE_JOIN} {where_clause} "
            f"ORDER BY r.crawled_at_text DESC LIMIT :limit OFFSET :offset"
        )
        params["limit"] = page_size
        params["offset"] = offset
        result = await self.db.execute(query_sql, params)
        rows = result.mappings().all()

        return [dict(r) for r in rows], total

    async def get_by_id(self, job_id: int) -> dict | None:
        """根据 ID 获取单条爬虫岗位详情（含 stack 分类）"""
        query_sql = text(f"""
            SELECT r.id, r.standardized_title, r.title, r.company, r.city,
                   r.salary_text, r.experience_text, r.education_text,
                   r.jd_text, r.responsibilities, r.requirements,
                   r.keywords, r.posted_at_text, r.crawled_at_text,
                   r.source_document_id,
                   sj.stack, sj.name AS std_job_name
            {self.BASE_JOIN}
            WHERE r.id = :job_id
        """)
        result = await self.db.execute(query_sql, {"job_id": job_id})
        row = result.mappings().first()
        return dict(row) if row else None
