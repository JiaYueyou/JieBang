"""
学习服务 —— 学习路径 CRUD + AI 学习助手。

Agent 2: 学习助手智能体
- 对话式问答（结合知识图谱上下文）
- 学习路径自动生成
- 学习资源推荐
- 学习成果测试生成
"""
import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.repositories.learning_repository import LearningRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository
from app.core.neo4j import run_read
from app.providers.llm import get_llm_provider


class LearningService:
    """学习路径管理 + AI 学习助手"""

    def __init__(self, db: AsyncSession):
        self.repo = LearningRepository(db)
        self.resume_repo = ResumeRepository(db)
        self.position_repo = PositionRepository(db)
        self.db = db
        self.llm = get_llm_provider()

    # ===== 学习路径 CRUD =====

    async def list_paths(self, user_id: int) -> list[dict]:
        """列出用户的所有学习路径"""
        paths = await self.repo.list_by_user(user_id)
        return [self._path_to_dict(p) for p in paths]

    async def get_path(self, path_id: int) -> dict:
        """获取单个学习路径详情"""
        path = await self.repo.get_by_id(path_id)
        if not path:
            raise ResourceNotFoundError("学习路径不存在")
        return self._path_to_dict(path)

    async def create_path(self, user_id: int, data: dict) -> dict:
        """创建学习路径"""
        position = await self.position_repo.get_by_id(data["position_id"])
        path = await self.repo.create(user_id, {
            "name": data["name"],
            "position_id": data["position_id"],
            "position_name": position.name if position else "",
            "steps": [],
            "total_duration": "",
        })
        await self.db.commit()
        return self._path_to_dict(path)

    async def update_path(self, path_id: int, data: dict) -> dict:
        """更新学习路径（名称、步骤、完成状态）"""
        path = await self.repo.get_by_id(path_id)
        if not path:
            raise ResourceNotFoundError("学习路径不存在")

        update_data = {}
        if data.get("name") is not None:
            update_data["name"] = data["name"]
        if data.get("steps") is not None:
            update_data["steps"] = data["steps"]
            # 自动计算总时长
            total_weeks = sum(
                int(s.get("duration", "0").replace("周", "").replace("-", " ").split()[0] or 0)
                for s in data["steps"]
            )
            update_data["total_duration"] = f"{total_weeks}周" if total_weeks > 0 else ""

        await self.repo.update(path, **update_data)
        await self.db.commit()
        await self.db.refresh(path)
        return self._path_to_dict(path)

    async def delete_path(self, path_id: int):
        """删除学习路径"""
        path = await self.repo.get_by_id(path_id)
        if not path:
            raise ResourceNotFoundError("学习路径不存在")
        await self.repo.delete(path)
        await self.db.commit()

    # ===== AI 学习助手 =====

    async def chat(self, message: str, context: dict | None, history: list[dict]) -> dict:
        """
        AI 学习助手对话 —— 结合知识图谱上下文回答问题。
        支持职业咨询、技术解释、学习建议等。
        """
        # 构建图谱上下文
        graph_context = ""
        if context and context.get("target_position_id"):
            graph_context = self._build_graph_context(context["target_position_id"])

        # 构建用户上下文
        user_context = ""
        if context and context.get("resume_id"):
            resume = await self.resume_repo.get_by_id(context["resume_id"])
            if resume:
                user_context = f"用户简历技能: {resume.skill_list}"

        messages = [
            {"role": "system", "content": (
                "你是专业的学习导师和职业规划顾问。你的任务是：\n"
                "1. 结合知识图谱中的岗位-技能关系，给出准确的职业建议\n"
                "2. 解释技术概念时，说明前置知识和学习路径\n"
                "3. 推荐具体的学习资源（课程、书籍、项目）\n"
                "4. 回答简洁专业，用 Markdown 格式\n"
                f"\n当前知识图谱上下文:\n{graph_context}\n{user_context}"
            )},
        ]
        # 添加历史对话
        for h in history[-10:]:  # 只保留最近 10 轮
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        try:
            response = await self.llm.chat(messages)
            reply = response.get("content", "抱歉，我暂时无法回答这个问题。")
        except Exception:
            reply = "AI 助手暂时不可用，请稍后重试。"

        # 从图谱中提取关联概念
        related = self._extract_related_concepts(message)

        # 从图谱中推荐相关资源
        resources = self._recommend_resources_from_graph(message)

        return {
            "reply": reply,
            "related_concepts": related,
            "suggested_resources": resources,
            "follow_up_questions": self._generate_follow_ups(message),
        }

    async def generate_path(self, position_id: int, resume_id: int | None = None) -> dict:
        """
        AI 自动生成学习路径 —— 根据目标岗位和用户现状生成个性化学习计划。
        图谱提供技能依赖关系 → 决定学习顺序；LLM 生成步骤描述和资源推荐。
        """
        position = await self.position_repo.get_by_id(position_id)
        if not position:
            raise ResourceNotFoundError("岗位不存在")

        # 从 Neo4j 查询岗位的技能树（含依赖关系）
        skill_tree = []
        try:
            skill_tree = run_read(
                "MATCH (p:Position {id: $pid})-[:COMPOSES]->(s:SkillsetBranch)-[:CONTAINS]->(m:Module)"
                "-[:INCLUDES]->(k:Knowledge) "
                "RETURN s.label AS skillset, m.label AS module, collect(k.label) AS knowledge",
                {"pid": str(position_id)},
            )
        except Exception:
            pass

        # 获取用户已有技能
        user_skills = set()
        if resume_id:
            resume = await self.resume_repo.get_by_id(resume_id)
            if resume:
                user_skills = set(s.get("name", "") for s in (resume.skill_list or []))

        # 组装 Prompt
        required_skills_str = ", ".join(
            [s.name for s in (position.required_skills or [])]
        )
        skill_tree_str = json.dumps(skill_tree, ensure_ascii=False) if skill_tree else "暂无图谱数据"
        user_skills_str = ", ".join(user_skills) if user_skills else "未知"

        messages = [
            {"role": "system", "content": (
                "你是学习路径设计师。根据目标岗位的技能要求、知识图谱的技能依赖关系、"
                "以及用户现有技能，设计一个分步骤的学习路径。\n"
                "输出 JSON: {\"name\": \"路径名\", \"steps\": [{\"title\": \"步骤名\", "
                "\"description\": \"描述\", \"duration\": \"X周\", "
                "\"resources\": [{\"title\": \"资源名\", \"type\": \"course/book/article/video\", "
                "\"url\": \"\", \"platform\": \"推荐平台\"}]}]}"
            )},
            {"role": "user", "content": (
                f"目标岗位: {position.name}\n"
                f"必备技能: {required_skills_str}\n"
                f"图谱技能树: {skill_tree_str}\n"
                f"用户已有技能: {user_skills_str}\n"
                f"请设计学习路径（4-6 个步骤，按技能依赖关系排序，先基础后进阶）。"
            )},
        ]

        try:
            response = await self.llm.chat(messages, response_format={"type": "json_object"})
            plan = json.loads(response.get("content", "{}"))
            if isinstance(plan, list):
                plan = {"name": f"{position.name}学习路径", "steps": plan}
        except Exception:
            plan = {"name": f"{position.name}学习路径", "steps": []}

        # 为每个 step 生成 ID
        steps = []
        total_weeks = 0
        for i, step in enumerate(plan.get("steps", [])):
            step["id"] = f"step-{uuid.uuid4().hex[:8]}"
            step["order"] = i + 1
            step["completed"] = False
            if "resources" not in step:
                step["resources"] = []
            for res in step.get("resources", []):
                if "id" not in res:
                    res["id"] = f"res-{uuid.uuid4().hex[:8]}"
            steps.append(step)
            # 估算时长
            dur = step.get("duration", "1周")
            try:
                total_weeks += int(dur.replace("周", "").split("-")[0])
            except ValueError:
                total_weeks += 1

        return {
            "name": plan.get("name", f"{position.name}学习路径"),
            "position_id": position_id,
            "position_name": position.name,
            "steps": steps,
            "total_duration": f"{total_weeks}周",
        }

    async def recommend_resources(self, skill_names: list[str]) -> dict:
        """根据技能名称推荐学习资源"""
        result = {}
        for skill in skill_names:
            # 优先从图谱查找关联资源
            resources = self._recommend_resources_from_graph(skill)
            if not resources:
                resources = [
                    {"id": f"res-{uuid.uuid4().hex[:8]}", "title": f"{skill}基础教程", "type": "course", "url": "", "platform": "推荐搜索"},
                    {"id": f"res-{uuid.uuid4().hex[:8]}", "title": f"{skill}实战项目", "type": "project", "url": "", "platform": "GitHub"},
                ]
            result[skill] = resources
        return {"skills": result}

    async def generate_quiz(self, path_id: int, step_ids: list[str], question_count: int) -> dict:
        """根据学习进度生成测试题"""
        path = await self.repo.get_by_id(path_id)
        if not path:
            raise ResourceNotFoundError("学习路径不存在")

        # 筛选出需要测试的步骤
        steps = path.steps or []
        if step_ids:
            steps = [s for s in steps if s.get("id") in step_ids]

        topics = [s.get("title", "") for s in steps if s.get("completed")]
        if not topics:
            topics = [s.get("title", "") for s in steps[:2]]

        messages = [
            {"role": "system", "content": (
                "你是在线教育测试专家。根据学习内容生成选择题和简答题。"
                "输出 JSON: {\"questions\": [{\"id\": \"q-1\", \"type\": \"choice\", "
                "\"question\": \"题目\", \"options\": [\"A\", \"B\", \"C\", \"D\"], "
                "\"correctAnswer\": 0, \"explanation\": \"解析\"}]}"
            )},
            {"role": "user", "content": (
                f"学习内容: {', '.join(topics)}\n"
                f"题目数量: {question_count}\n"
                f"请生成测试题。"
            )},
        ]

        try:
            response = await self.llm.chat(messages, response_format={"type": "json_object"})
            quiz = json.loads(response.get("content", "{}"))
            questions = quiz.get("questions", [])
        except Exception:
            questions = []

        # 为每个题目生成唯一 ID
        for q in questions:
            if "id" not in q:
                q["id"] = f"q-{uuid.uuid4().hex[:8]}"

        return {"questions": questions}

    # ===== 辅助方法 =====

    def _build_graph_context(self, position_id: int) -> str:
        """从 Neo4j 构建岗位所属的知识图谱上下文"""
        try:
            nodes = run_read(
                "MATCH (p:Position {id: $pid})-[:COMPOSES*1..3]->(related) "
                "RETURN related.label AS label, related.type AS type",
                {"pid": str(position_id)},
            )
            if nodes:
                return "岗位关联的技能和知识点:\n" + "\n".join(
                    f"- {n['label']} ({n['type']})" for n in nodes
                )
        except Exception:
            pass
        return ""

    def _extract_related_concepts(self, message: str) -> list[dict]:
        """从图谱中提取与用户问题相关的概念节点"""
        try:
            results = run_read(
                "MATCH (n) WHERE n.label CONTAINS $keyword "
                "RETURN n.id AS id, n.label AS label, n.type AS type LIMIT 5",
                {"keyword": message[:10]},
            )
            return [{"name": r["label"], "node_id": r["id"], "relation": r["type"]} for r in results]
        except Exception:
            return []

    def _recommend_resources_from_graph(self, query: str) -> list[dict]:
        """从图谱中查找与查询相关的学习资源"""
        # 图谱目前主要存储技能关系，资源推荐依赖 LLM。
        # 此处返回空列表，由 LLM 生成推荐。
        return []

    def _generate_follow_ups(self, message: str) -> list[str]:
        """根据用户问题生成建议追问"""
        if "学习" in message or "转行" in message:
            return ["需要哪些前置知识？", "学习周期大概多久？", "有哪些推荐的学习资源？"]
        if "是什么" in message or "解释" in message:
            return ["这个技术的应用场景是什么？", "学习它的前置要求是什么？"]
        return ["能详细说说吗？", "有什么实际应用场景？"]

    def _path_to_dict(self, p) -> dict:
        """将 LearningPath 模型转为 API 返回格式"""
        return {
            "id": p.id,
            "name": p.name,
            "position_id": p.position_id,
            "position_name": p.position_name,
            "steps": p.steps or [],
            "total_duration": p.total_duration or "",
            "created_at": str(p.created_at) if p.created_at else None,
            "updated_at": str(p.updated_at) if p.updated_at else None,
        }
