"""
简历服务 —— 简历 CRUD、文件上传解析。
"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.resume_repository import ResumeRepository
from app.core.neo4j import run_read


class ResumeService:
    """简历业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.repo = ResumeRepository(db)
        self.db = db

    async def list_resumes(self, user_id: int) -> list[dict]:
        """列出用户的所有简历"""
        resumes = await self.repo.list_by_user(user_id)
        return [self._to_dict(r) for r in resumes]

    async def get_detail(self, resume_id: int) -> dict:
        """获取简历详情"""
        resume = await self.repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")
        return self._to_dict(resume)

    async def create(self, user_id: int, data: dict) -> dict:
        """手动创建简历（支持完整字段）"""
        create_data = self._build_resume_data(data)
        create_data["name"] = data.get("name", "我的简历")
        resume = await self.repo.create(user_id, create_data)
        await self.db.commit()
        return self._to_dict(resume)

    async def update(self, resume_id: int, data: dict) -> dict:
        """更新简历内容"""
        resume = await self.repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")

        update_data = self._build_resume_data(data)
        await self.repo.update(resume, **update_data)
        await self.db.commit()
        await self.db.refresh(resume)
        return self._to_dict(resume)

    def _build_resume_data(self, data: dict) -> dict:
        """将前端传来的结构化字段映射为数据库列名"""
        result: dict = {}

        if data.get("personal_info"):
            pi = data["personal_info"]
            result.update({
                "personal_name": pi.get("name", ""),
                "personal_email": pi.get("email", ""),
                "personal_phone": pi.get("phone", ""),
                "personal_location": pi.get("location", ""),
            })
        if data.get("job_intent"):
            ji = data["job_intent"]
            result.update({
                "desired_position": ji.get("desired_position", ""),
                "desired_city": ji.get("desired_city", ""),
                "salary_expectation": ji.get("salary_expectation", ""),
                "work_mode": ji.get("work_mode", "fulltime"),
            })
        if data.get("education") is not None:
            result["education_list"] = data["education"]
        if data.get("work_experience") is not None:
            result["work_experience_list"] = data["work_experience"]
        if data.get("projects") is not None:
            result["project_list"] = data["projects"]
        if data.get("skills") is not None:
            result["skill_list"] = data["skills"]

        for front_key, db_key in (("name", "name"), ("target_position", "target_position"), ("self_evaluation", "self_evaluation")):
            if data.get(front_key) is not None:
                result[db_key] = data[front_key]

        return result

    async def delete(self, resume_id: int):
        """删除简历"""
        resume = await self.repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")
        await self.repo.delete(resume)
        await self.db.commit()

    async def duplicate(self, resume_id: int) -> dict:
        """复制简历"""
        resume = await self.repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")
        new_resume = await self.repo.duplicate(resume)
        await self.db.commit()
        return self._to_dict(new_resume)

    async def parse_upload(self, user_id: int, file_content: bytes, filename: str) -> dict:
        """
        上传并解析简历文件。
        TODO: 对接讯飞文档解析 API 进行 OCR + NER 提取。
        当前为占位实现，返回模拟的解析结果。
        """
        # 创建简历记录
        resume = await self.repo.create(user_id, {
            "name": Path(filename).stem,
            "source_file": filename,
        })
        await self.db.commit()

        # TODO: 替换为真实的文档解析流程
        # 1. 调用讯飞文档解析 API 将 PDF/Word 转为纯文本
        # 2. 使用微调 BERT-CRF 模型提取结构化字段
        # 3. 将提取的技能映射到标准技能词表（从 Neo4j 图谱获取别名）
        extracted_skills = ["Java", "Spring Boot", "MySQL"]
        parse_accuracy = 0.85  # 占位准确率

        return {
            "resume": self._to_dict(resume),
            "extracted_skills": extracted_skills,
            "parse_accuracy": parse_accuracy,
        }

    def _to_dict(self, r) -> dict:
        """将 Resume 模型转为 API 返回格式"""
        return {
            "id": r.id,
            "name": r.name,
            "target_position": r.target_position,
            "personal_info": {
                "name": r.personal_name, "email": r.personal_email,
                "phone": r.personal_phone, "location": r.personal_location,
            },
            "job_intent": {
                "desired_position": r.desired_position or "",
                "desired_city": r.desired_city or "",
                "salary_expectation": r.salary_expectation or "",
                "work_mode": r.work_mode or "fulltime",
            },
            "education": r.education_list or [],
            "work_experience": r.work_experience_list or [],
            "projects": r.project_list or [],
            "skills": r.skill_list or [],
            "self_evaluation": r.self_evaluation or "",
            "source_file": r.source_file,
            "created_at": str(r.created_at) if r.created_at else None,
            "updated_at": str(r.updated_at) if r.updated_at else None,
        }
