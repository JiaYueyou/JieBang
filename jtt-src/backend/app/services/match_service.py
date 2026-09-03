"""
匹配服务 —— 人岗匹配评分算法、差距分析。
数据源：raw_job_record 优先，Neo4j 知识图谱次之，MySQL job_position 兜底。
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ResourceNotFoundError
from app.core.neo4j import run_read_async
from app.providers.llm import get_llm_provider
from app.repositories.match_repository import MatchRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.position_repository import PositionRepository
from app.repositories.raw_job_repository import RawJobRepository
from app.repositories.graph_repository import Neo4jGraphRepository

logger = logging.getLogger(__name__)

# 学历排序权重，用于比较学历高低
EDUCATION_RANK = {"博士": 5, "硕士": 4, "本科": 3, "大专": 2, "高中": 1, "中专": 1}

# 从 JD 文本中提取的技术关键词（大小写不敏感，含英文和中国技术词）
TECH_KEYWORDS = [
    # 编程语言
    "Python", "Java\\b(?!\\s*Script)", "C\\+\\+", "C#", "Go\\b(?!\\s*lang)", "Golang",
    "Rust", "JavaScript", "TypeScript", "Shell", "Bash", "Scala", "Kotlin",
    "MATLAB", "PHP", "Ruby", "Perl", "Lua", "Swift", "Objective-C",
    "SQL", "R\\b(?!\\w)", "Verilog",
    # Java 生态
    "Spring Boot", "Spring Cloud", "Spring MVC", "Spring",
    "MyBatis", "Mybatis", "Hibernate", "JPA", "Struts", "Netty",
    "Maven", "Gradle", "JVM", "Tomcat", "Jetty",
    # Python 生态
    "Django", "Flask", "FastAPI", "Tornado", "Celery",
    "NumPy", "Pandas", "Scikit-learn", "Scipy",
    # 前端
    "Vue", "React", "Angular", "Node\\.js", "Next\\.js", "Nuxt",
    "Webpack", "Vite", "Babel", "ES6", "HTML5", "CSS3", "Sass", "Less",
    "Electron", "Flutter", "React Native", "小程序",
    # 数据库 / 存储
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "ES\\b",
    "Oracle", "SQLite", "MariaDB", "Cassandra", "HBase", "Hive",
    "ClickHouse", "TiDB", "InfluxDB", "Neo4j", "MinIO", "Ceph",
    "Memcache", "ETCD",
    # 消息 / 中间件
    "Docker", "Kubernetes", "K8s", "Jenkins", "Git", "GitLab", "GitHub",
    "Nginx", "Apache", "RabbitMQ", "Kafka", "RocketMQ", "ZooKeeper",
    "Nacos", "Consul", "Apollo", "SkyWalking", "Prometheus", "Grafana",
    "ELK", "Logstash", "Kibana",
    # 大数据
    "Hadoop", "Spark", "Flink", "Storm", "HDFS", "YARN",
    "Hive", "Presto", "Druid", "Kylin", "Airflow", "DolphinScheduler",
    # AI / ML
    "TensorFlow", "PyTorch", "Keras", "Caffe", "MXNet",
    "NLP", "CV", "RAG", "LangChain", "LLM", "Agent", "Transformer",
    "机器学习", "深度学习", "自然语言处理", "计算机视觉", "大模型",
    "强化学习", "迁移学习", "知识图谱",
    # 通信 / 协议
    "TCP/IP", "HTTP", "HTTPS", "REST", "RESTful", "gRPC", "WebSocket",
    "MQTT", "Protobuf", "JSON", "XML",
    # 云平台
    "AWS", "Azure", "GCP", "阿里云", "腾讯云", "华为云",
    # 操作系统
    "Linux", "Unix", "CentOS", "Ubuntu", "Windows Server",
    "Android", "iOS", "嵌入式", "RTOS",
    # 通用技术概念/架构
    "微服务", "分布式", "高并发", "多线程", "云原生", "容器化",
    "CI/CD", "DevOps", "敏捷开发", "TDD", "DDD",
    "JWT", "OAuth", "SSO", "RBAC",
    # 芯片/硬件
    "ARM", "FPGA", "GPU", "CUDA", "DSP",
    # 音视频
    "FFmpeg", "WebRTC", "OpenGL", "OpenCV",
    # 项目管理
    "Jira", "Confluence", "禅道",
]

# 编译正则：只匹配独立技术词（非单词片段）
_TECH_RE = re.compile(
    r'\b(' + '|'.join(TECH_KEYWORDS) + r')\b',
    re.IGNORECASE,
)

# 中文技术词单独匹配（无单词边界）
_CHINESE_TECH = ["微服务", "分布式", "高并发", "多线程", "云原生", "机器学习", "深度学习", "自然语言处理", "计算机视觉"]
_CHINESE_TECH_RE = re.compile('|'.join(_CHINESE_TECH))


def _extract_skills_from_text(text: str) -> list[str]:
    """从文本中提取技术关键词，返回去重后的技能名列表"""
    if not text:
        return []
    # 英文技术词（用单词边界匹配）
    english_matches = [m.group(0).strip() for m in _TECH_RE.finditer(text)]
    # 中文技术词
    chinese_matches = _CHINESE_TECH_RE.findall(text) if text else []
    # 去重并规范大小写
    seen = set()
    result = []
    for skill in english_matches + chinese_matches:
        norm = skill.lower()
        # 统一几个常见缩写
        norm = norm.replace("k8s", "kubernetes")
        if norm not in seen:
            seen.add(norm)
            result.append(skill)
    return result


def _skill_tokens(name: str) -> set[str]:
    """技能名拆分为词元集合：按 / 、空格 括号等分隔并转小写，用于模糊匹配"""
    parts = re.split(r"[/、，,（）()\s]+", name.strip())
    return {p.lower() for p in parts if p}


def _has_cjk(s: str) -> bool:
    """判断是否含中文字符"""
    return any("一" <= c <= "鿿" for c in s)


def _skill_names_match(resume_skill: str, position_skill: str) -> bool:
    """
    判断简历技能与岗位技能是否等价（模糊匹配）：
    - 全名相等（忽略大小写）
    - 词元交集：如 "LangChain" ↔ "LangChain / LangGraph"、"RAG" ↔ "RAG 检索增强生成"
    - 中文包含关系：如 "微服务" ↔ "微服务架构"
    """
    a, b = resume_skill.strip().lower(), position_skill.strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    if _skill_tokens(resume_skill) & _skill_tokens(position_skill):
        return True
    if _has_cjk(a) or _has_cjk(b):
        return a in b or b in a
    return False


def _parse_education_requirement(text: str) -> str:
    """从文本中提取学历要求，返回 '博士'/'硕士'/'本科'/'大专'/'高中' 或空字符串"""
    if not text:
        return ""
    for keyword in ["博士", "硕士", "本科", "大专", "高中", "中专"]:
        if keyword in text:
            return keyword
    return ""


def _education_meets(requirement: str, resume_education: str) -> bool:
    """检查简历学历是否满足岗位学历要求"""
    if not requirement:
        return True
    req_rank = EDUCATION_RANK.get(requirement, 0)
    resume_rank = max(
        (EDUCATION_RANK.get(edu.get("degree", ""), 0) for edu in ([{"degree": resume_education}] if resume_education else [])),
        default=0,
    )
    return resume_rank >= req_rank




class MatchService:
    """人岗匹配业务逻辑"""

    def __init__(self, db: AsyncSession):
        self.match_repo = MatchRepository(db)
        self.resume_repo = ResumeRepository(db)
        self.position_repo = PositionRepository(db)
        self.raw_job_repo = RawJobRepository(db)
        self.graph_repo = Neo4jGraphRepository()
        self.db = db

    # ===== 数据源加载 =====

    async def _load_jobs_from_raw_record(self) -> list[dict]:
        """从 MySQL raw_job_record 加载所有岗位为匹配用的标准化格式（单次批量查询，避免 N+1）"""
        rows = await self.raw_job_repo.get_all()
        return [self._normalize_raw_job(row) for row in rows]

    async def _load_jobs_from_neo4j(self) -> list[dict]:
        """从 Neo4j 加载所有 Job 节点为匹配用的标准化格式（同步驱动放线程池执行，避免阻塞事件循环）"""
        neo4j_jobs = await asyncio.to_thread(self.graph_repo.query_jobs_for_matching)
        return [self._normalize_neo4j_job(j) for j in neo4j_jobs]

    async def _load_jobs_from_mysql(self) -> list[dict]:
        """从 MySQL job_position 加载所有岗位为匹配用的标准化格式"""
        all_ids = await self.position_repo.get_all_ids()
        positions = []
        for pid in all_ids:
            pos = await self.position_repo.get_by_id(pid)
            if not pos:
                continue
            skills = await self.position_repo.get_skills_for_positions([pid])
            pos_skills = skills.get(pid, [])
            positions.append(self._normalize_mysql_job(pos, pos_skills))
        return positions

    def _normalize_raw_job(self, row: dict) -> dict:
        """将 raw_job_record 行转为标准岗位格式"""
        # 从 requirements 文本提取详细技能
        req_text = (row.get("requirements") or "") + " " + (row.get("jd_text") or "")
        extracted_skills = _extract_skills_from_text(req_text)
        # 合并 keywords（逗号分隔）和提取的技能
        kw_text = (row.get("keywords") or "")
        kw_skills = [k.strip() for k in kw_text.split(",") if k.strip()]
        all_skills = list(set(kw_skills + extracted_skills))
        # 学历：优先用 education_text，否则从 requirements 解析
        edu_text = row.get("education_text") or ""
        education_req = _parse_education_requirement(edu_text) or _parse_education_requirement(req_text)
        return {
            "id": f"raw:{row['id']}",
            "name": row.get("standardized_title") or row.get("title") or "",
            "description": req_text,
            "stack": row.get("stack", ""),
            "education_requirement": education_req,
            "required_skills": all_skills,
            "preferred_skills": [],
            "all_skills": all_skills,
            "source": "raw_job_record",
        }

    def _normalize_neo4j_job(self, job: dict) -> dict:
        """将 Neo4j 节点转为标准岗位格式"""
        all_skills = list(set(job["skills"] + job["tech_points"] + job["knowledge_points"]))
        description = job.get("description", "")
        return {
            "id": job["id"],
            "name": job["name"],
            "description": description,
            "stack": job.get("stack", ""),
            "education_requirement": _parse_education_requirement(description),
            "required_skills": job["skills"],
            "preferred_skills": job["tech_points"],
            "all_skills": all_skills,
            "source": "neo4j",
        }

    def _normalize_mysql_job(self, position, position_skills: list[dict]) -> dict:
        """将 MySQL 岗位 + 技能转为标准岗位格式"""
        required = [s["name"] for s in position_skills if s.get("kind") == "required"]
        preferred = [s["name"] for s in position_skills if s.get("kind") == "preferred"]
        description = (position.summary or "") + " " + " ".join(position.responsibilities or [])
        return {
            "id": f"position:{position.id}",
            "name": position.name,
            "description": description,
            "stack": "",
            "education_requirement": _parse_education_requirement(description),
            "required_skills": required,
            "preferred_skills": preferred,
            "all_skills": required + preferred,
            "source": "mysql",
        }

    # ===== 学历筛选 =====

    def _get_resume_highest_education(self, resume) -> str:
        """从简历教育经历中提取最高学历"""
        edu_list = resume.education_list or []
        best_rank = 0
        best_edu = ""
        for edu in edu_list:
            degree = edu.get("degree", "") if isinstance(edu, dict) else ""
            rank = EDUCATION_RANK.get(degree, 0)
            if rank > best_rank:
                best_rank = rank
                best_edu = degree
        return best_edu

    # ===== 核心匹配 =====

        # ── [Agent 3] 技能图谱背书（防幻觉）──
    async def _graph_verified_skills(self, position_name: str) -> set[str]:
        """
        查知识图谱获取该岗位技能树（TechStack/TechPoint/KnowledgePoint 三层），
        返回图谱中真实存在的技能名集合（小写）。Neo4j 不可用返回空集。
        异步执行：Neo4j 同步驱动放线程池，避免阻塞事件循环。
        """
        try:
            rows = await run_read_async(
                "MATCH (j:Job {name: $job})-[:REQUIRES_AREA]->(:SkillArea)-[:CONTAINS]->(ts:TechStack) "
                "OPTIONAL MATCH (ts)-[:SUPPORTS]->(tp:TechPoint) "
                "OPTIONAL MATCH (tp)-[:HAS_KNOWLEDGE]->(kp:KnowledgePoint) "
                "RETURN collect(DISTINCT ts.name)+collect(DISTINCT tp.name)+collect(DISTINCT kp.name) AS skills",
                {"job": position_name},
            )
            if not rows:
                return set()
            return {str(n).strip().lower() for n in (rows[0].get("skills") or []) if n}
        except Exception:
            return set()

    async def _graph_skills_map(self, position_names: set[str]) -> dict[str, set[str]]:
        """
        一次性批量查询多个岗位的技能树，返回 {岗位名: 技能集合}。
        批量匹配时用一条查询替代逐岗位查询，避免 N 次全表扫描放大的耗时。Neo4j 不可用返回空 dict。
        异步执行：Neo4j 同步驱动放线程池，避免阻塞事件循环。
        """
        names = [n for n in position_names if n]
        if not names:
            return {}
        try:
            rows = await run_read_async(
                "MATCH (j:Job)-[:REQUIRES_AREA]->(:SkillArea)-[:CONTAINS]->(ts:TechStack) "
                "OPTIONAL MATCH (ts)-[:SUPPORTS]->(tp:TechPoint) "
                "OPTIONAL MATCH (tp)-[:HAS_KNOWLEDGE]->(kp:KnowledgePoint) "
                "WHERE j.name IN $names "
                "RETURN j.name AS job, collect(DISTINCT ts.name)+collect(DISTINCT tp.name)+collect(DISTINCT kp.name) AS skills",
                {"names": names},
            )
            result: dict[str, set[str]] = {}
            for row in rows:
                job = row.get("job")
                if not job:
                    continue
                result[str(job)] = {
                    str(n).strip().lower() for n in (row.get("skills") or []) if n
                }
            return result
        except Exception:
            return {}

    # ── [Agent 3] 技能语义匹配（LLM）──
    async def _semantic_skill_match(self, resume_skills: list[str], position_skills: list[str]) -> set[str]:
        """
        使用 LLM 对技能进行语义匹配：判断岗位技能是否被简历技能语义覆盖。
        例："懂 Python 数据分析" ↔ "Pandas/NumPy 经验"、"微服务" ↔ "Spring Cloud 分布式"。
        返回被覆盖的岗位技能集合。LLM 不可用时降级为规则模糊匹配。
        """
        try:
            provider = get_llm_provider()
            prompt = (
                "你是人岗匹配专家。判断以下候选人的技能是否能覆盖目标岗位的技能要求。\n"
                "忽略字面差异，只判断**语义上的覆盖关系**。例如：\n"
                "- 候选人技能 'Python 数据分析' 能覆盖岗位技能 'Pandas/NumPy 经验'\n"
                "- 候选人技能 'Spring Boot' 能覆盖岗位技能 '微服务开发'\n\n"
                f"候选人技能：{', '.join(resume_skills) or '无'}\n\n"
                f"目标岗位技能：{', '.join(position_skills) or '无'}\n\n"
                '输出严格的 JSON：{"matched": ["被覆盖的岗位技能名", ...]}\n'
                "只返回确实被覆盖的岗位技能，不要编造。"
            )
            result = await provider.chat(
                [{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
            candidates = set(parsed.get("matched", []) or [])
            # 防幻觉：只保留确实存在于岗位技能列表中的结果
            valid = candidates & set(position_skills)
            if valid:
                return valid
            raise ValueError("LLM 未返回有效匹配")
        except Exception:
            # 降级为规则模糊匹配
            return {
                ps for ps in position_skills
                if any(_skill_names_match(rs, ps) for rs in resume_skills)
            }

    # ── [Agent 3] 经验相关性评估（LLM）──
    async def _assess_experience_relevance(
        self, work_experience: list[dict], position_name: str, position_skills: list[str]
    ) -> int:
        """
        使用 LLM 评估工作经历与目标岗位的相关性，返回 0-100 分。
        考虑：行业是否对口、职责是否匹配、经验年限、技能相关性。
        无工作经历返回 0。LLM 不可用时降级为基于经历数量的评分。
        """
        if not work_experience:
            return 0
        try:
            provider = get_llm_provider()
            exp_text = "\n".join(
                f"- {e.get('position', '')} @ {e.get('company', '')}: {e.get('description', '')}"
                for e in work_experience
            )
            prompt = (
                "你是人岗匹配专家。评估以下候选人的工作经历与目标岗位的相关性，给出 0-100 分。\n"
                "考虑：行业是否对口、职责是否匹配、经验年限、技能相关性。\n\n"
                f"目标岗位：{position_name}\n"
                f"岗位技能要求：{', '.join(position_skills) or '无'}\n\n"
                f"候选人工作经历：\n{exp_text}\n\n"
                '输出严格的 JSON：{"score": 0到100的整数, "reason": "简要理由"}'
            )
            result = await provider.chat(
                [{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
            )
            parsed = json.loads(result["content"])
            score = parsed.get("score")
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                raise ValueError("LLM 未返回有效分数")
            return int(score)
        except Exception:
            # 降级：基于经历数量
            work_count = len(work_experience)
            return min(100, 40 + work_count * 20) if work_count > 0 else 30

    async def do_match(self, user_id: int, resume_id: int, job: dict, persist: bool = True,
                       _fast_match: bool = False, _resume_ctx: dict | None = None,
                       _graph_ctx: dict[str, set[str]] | None = None) -> dict | None:
        """执行单次人岗匹配。job 为标准化格式的岗位字典。返回 None 表示被学历过滤。
        persist=False 时只计算不持久化（用于批量实时匹配）。
        _fast_match=True：批量模式，跳过逐岗位 LLM 调用（规则+图谱匹配），快百倍。
        _graph_ctx：批量模式预加载的图谱技能映射 {岗位名: 技能集合}，避免逐岗位查 Neo4j。"""
        if _fast_match and _resume_ctx is not None:
            resume = None  # 批量模式：简历数据来自 _resume_ctx，不重复查库
        else:
            resume = await self.resume_repo.get_by_id(resume_id)
            if not resume:
                raise ResourceNotFoundError("简历不存在")

        # 学历硬筛选（批量模式无 resume 对象时跳过学历过滤）
        if resume is not None:
            resume_edu = self._get_resume_highest_education(resume)
            if not _education_meets(job.get("education_requirement", ""), resume_edu):
                return None

        # 岗位名 + 图谱技能树：批量匹配用预加载映射，单次匹配按需查询（仅查一次，复用）
        position_name = job["name"]
        graph_skills = (
            _graph_ctx.get(position_name, set())
            if _graph_ctx is not None
            else await self._graph_verified_skills(position_name)
        )

        resume_skill_names = (
            _resume_ctx["skills"] if (_fast_match and _resume_ctx)
            else [s.get("name", "") for s in (resume.skill_list or []) if s.get("name")]
        )
        required_skills = set(job.get("required_skills", []))
        preferred_skills = set(job.get("preferred_skills", []))
        all_position_skills = required_skills | preferred_skills

        # 1) 技能匹配评分 (50%)
        if _fast_match:
            # 批量模式：规则模糊匹配 + 图谱验证（不调 LLM，毫秒级）
            matched = {
                ps for ps in all_position_skills
                if any(_skill_names_match(rs, ps) for rs in resume_skill_names)
            }
            graph_ok = graph_skills
            matched |= {ps for ps in all_position_skills
                        if ps.strip().lower() in graph_ok and any(
                            rs.lower() in ps.lower() or ps.lower() in rs.lower()
                            for rs in resume_skill_names)}
        else:
            # 单次模式：LLM 语义匹配，降级为规则模糊匹配
            matched = await self._semantic_skill_match(resume_skill_names, list(all_position_skills))
        missing = all_position_skills - matched
        required_matched = required_skills & matched
        required_missing = required_skills - matched

        if all_position_skills:
            req_ratio = len(required_matched) / len(required_skills) if required_skills else 1.0
            pref_ratio = (
                len(preferred_skills & matched) / len(preferred_skills)
                if preferred_skills else 1.0
            )
            skill_score = min(100, int(req_ratio * 70 + pref_ratio * 30))
        else:
            skill_score = 70

        # 2) 经验匹配评分 (35%)
        if _fast_match and _resume_ctx:
            work_experience = [
                {
                    "company": e.get("company", ""),
                    "position": e.get("position", ""),
                    "description": e.get("description", ""),
                    "skills": e.get("skills", []),
                }
                for e in _resume_ctx.get("exp", [])
            ]
            # 批量模式：规则评分（经验数+岗位名技能命中），不调 LLM
            work_count = len(work_experience)
            base = min(100, 40 + work_count * 20) if work_count > 0 else 30
            job_name = job.get("name", "")
            relevant = any(rs.lower() in job_name.lower() for rs in resume_skill_names)
            exp_score = min(100, base + (10 if relevant else 0))
        else:
            work_experience = [
                {
                    "company": e.get("company", ""),
                    "position": e.get("position", ""),
                    "description": e.get("description", ""),
                    "skills": e.get("skills", []),
                }
                for e in (resume.work_experience_list or [])
            ]
            work_count = len(work_experience)
            exp_score = await self._assess_experience_relevance(
                work_experience, job.get("name", ""), list(all_position_skills)
            )

        # 3) 综合素质评分 (15%)（批量模式 resume 为 None 时用默认中性分）
        if resume is not None:
            proj_count = len(resume.project_list or [])
            has_eval = bool(resume.self_evaluation and len(resume.self_evaluation) > 20)
            resume_edu_out = self._get_resume_highest_education(resume)
        else:
            proj_count, has_eval, resume_edu_out = 2, True, ""
        quality_score = min(100, proj_count * 25 + (25 if has_eval else 0))

        # 加权总分（技能 50% + 经验 35% + 综合素质 15%）
        total_score = int(
            skill_score * 0.50 + exp_score * 0.35 + quality_score * 0.15
        )

        # 构建维度详情
        position_name = job["name"]
        edu_status = (
            f"{resume_edu_out or '未知'} {'≥' if resume_edu_out else ''}{job.get('education_requirement', '无要求')}"
            if job.get("education_requirement") else "无硬性要求"
        )
        dimensions = [
            {"name": "技能匹配", "score": skill_score, "weight": 0.50,
             "details": f"匹配 {len(matched)}/{len(all_position_skills)} 项技能，缺失 {len(missing)} 项"},
            {"name": "经验匹配", "score": exp_score, "weight": 0.35,
             "details": f"{work_count} 段工作经历"},
            {"name": "综合素质", "score": quality_score, "weight": 0.15,
             "details": f"{proj_count} 个项目{'，有自我评价' if has_eval else ''}"},
            {"name": "学历要求", "score": 100 if resume_edu_out else 0, "weight": 0,
             "details": edu_status},
        ]

        # 构建差距分析
        gap_analysis = {
            "missing_skills": [
                {"name": s, "level": "required", "category": ""}
                for s in required_missing
            ],
            "weak_skills": [
                {"name": s, "level": "preferred", "category": ""}
                for s in (preferred_skills - matched)
            ],
            "match_skills": [
                {"name": s, "level": "required" if s in required_skills else "preferred", "category": ""}
                for s in matched
            ],
        }

        # 生成规则优化建议（经图谱验证标记；graph_skills 复用上方已查询结果，避免重复查 Neo4j）
        def _graph_flag(skill_name: str) -> dict:
            if not graph_skills or skill_name.strip().lower() in graph_skills:
                return {"verified": True, "warning": None}
            return {"verified": False, "warning": "该技能未在知识图谱岗位技能树中验证，请人工确认"}

        suggestions = []
        for i, skill_name in enumerate(required_missing):
            suggestions.append({
                "id": f"sg-{i+1}",
                "section": "skills", "field": "skills",
                "original": "", "suggested": f"建议学习并添加技能: {skill_name}",
                "reason": f"该岗位要求掌握 {skill_name}",
                "change_type": "large", "accepted": False,
                **_graph_flag(skill_name),
            })
        for j, skill_name in enumerate(preferred_skills - matched):
            suggestions.append({
                "id": f"sg-p{j+1}",
                "section": "skills", "field": "skills",
                "original": "", "suggested": f"建议补充加分技能: {skill_name}",
                "reason": f"掌握 {skill_name} 可显著提升该岗位竞争力",
                "change_type": "small", "accepted": False,
                **_graph_flag(skill_name),
            })

        # [P2] 匹配推理链 —— 真实数据驱动的可解释推理过程
        matched_list = sorted(matched, key=lambda s: (s not in required_skills, s))
        missing_required_list = sorted(required_missing)
        graph_hit_missing = [s for s in missing_required_list if s.strip().lower() in graph_skills] if graph_skills else []

        reasoning_chain = [
            {
                "icon": "📋", "title": "岗位要求解析",
                "detail": f"必备 {len(required_skills)} 项：{'、'.join(list(required_skills)[:6]) or '无'}"
                          + (f" 等；加分 {len(preferred_skills)} 项" if len(preferred_skills) > 6 else ""),
            },
            {
                "icon": "👤", "title": "候选人技能画像",
                "detail": f"简历提取 {len(resume_skill_names)} 项技能：{'、'.join(resume_skill_names[:6]) or '无'}"
                          + (" 等" if len(resume_skill_names) > 6 else ""),
            },
            {
                "icon": "🧩", "title": "语义匹配结果",
                "detail": (f"匹配 {len(matched_list)} 项：{'、'.join(matched_list[:6]) or '无'}"
                           + (f" 等（{len(matched)} 项全部命中）" if len(matched) > 6 else ""))
                          if matched_list else "未匹配到任何岗位技能",
            },
            {
                "icon": "🔍", "title": "知识图谱验证",
                "detail": (f"缺失技能中 {len(graph_hit_missing)}/{len(missing_required_list)} 项经图谱验证为该岗位技能树真实节点"
                           if graph_skills else "图谱暂未收录该岗位，匹配结果未经图谱背书"),
            },
        ]
        if missing_required_list:
            priority = graph_hit_missing[0] if graph_hit_missing else missing_required_list[0]
            reasoning_chain.append({
                "icon": "📚", "title": "补齐建议",
                "detail": f"优先学习 {priority}（{'图谱技能树节点，岗位核心要求' if graph_hit_missing else '岗位必备技能'}），预计可提升匹配度",
            })

        # 持久化（仅 MySQL 单次匹配需要保存，批量实时匹配不落库）
        result_id = 0
        if persist:
            try:
                position_id_str = job["id"].split(":", 1)[1]
                position_id = int(position_id_str)
            except (IndexError, ValueError):
                position_id = hash(job["id"]) % 100000

            match_data = {
                "resume_id": resume_id,
                "position_id": position_id,
                "position_name": position_name,
                "resume_name": (resume.name if resume else ""),
                "total_score": total_score,
                "dimensions": dimensions,
                "gap_analysis": gap_analysis,
                "suggestions": suggestions,
                "match_date": datetime.now(),
            }
            result = await self.match_repo.create(user_id, match_data)
            await self.db.commit()
            result_id = result.id

        return {
            "id": result_id,
            "resume_id": resume_id,
            "position_id": job["id"],
            "position_name": position_name,
            "resume_name": (resume.name if resume else ""),
            "total_score": total_score,
            "dimensions": dimensions,
            "gap_analysis": gap_analysis,
            "suggestions": suggestions,
            "reasoning_chain": reasoning_chain,
            "match_date": str(datetime.now()),
        }

    async def do_match_by_mysql_id(self, user_id: int, resume_id: int, position_id: int) -> dict | None:
        """通过 MySQL position_id 执行匹配（兼容旧接口），加载 MySQL 岗位数据后委托给 do_match"""
        position = await self.position_repo.get_by_id(position_id)
        if not position:
            raise ResourceNotFoundError("岗位不存在")
        skills_map = await self.position_repo.get_skills_for_positions([position_id])
        pos_skills = skills_map.get(position_id, [])
        job = self._normalize_mysql_job(position, pos_skills)
        return await self.do_match(user_id, resume_id, job)

    # ===== 批量 / 自动匹配 =====

    async def batch_match(self, user_id: int, resume_id: int, position_ids: list[int]) -> list[dict]:
        """批量匹配（一份简历 vs 多个 MySQL 岗位），兼容旧接口"""
        results = []
        for pid in position_ids:
            try:
                result = await self.do_match_by_mysql_id(user_id, resume_id, pid)
                if result is not None:
                    results.append(result)
            except ResourceNotFoundError:
                continue
        return results

    async def auto_match(self, user_id: int, resume_id: int) -> dict:
        """
        自动匹配简历与所有岗位，按综合分数降序返回诊断报告列表。
        数据源：raw_job_record 优先 → Neo4j 降级 → MySQL job_position 兜底。
        只返回 total_score >= 50 的结果。
        """
        jobs: list[dict] = []
        data_source = ""

        # 1) 优先 raw_job_record（190条，全有技能关键词）
        try:
            jobs = await self._load_jobs_from_raw_record()
            data_source = "raw_job_record"
            logger.info(f"auto_match: 从 raw_job_record 加载 {len(jobs)} 个岗位")
        except Exception as e:
            logger.warning(f"auto_match: raw_job_record 加载失败 ({e})，尝试 Neo4j")
            # 2) 降级 Neo4j
            try:
                jobs = await self._load_jobs_from_neo4j()
                data_source = "neo4j"
                logger.info(f"auto_match: 从 Neo4j 加载 {len(jobs)} 个岗位")
            except Exception as e2:
                logger.warning(f"auto_match: Neo4j 加载失败 ({e2})，回退到 MySQL")
                # 3) 兜底 MySQL job_position
                try:
                    jobs = await self._load_jobs_from_mysql()
                    data_source = "mysql"
                    logger.info(f"auto_match: 从 MySQL 加载 {len(jobs)} 个岗位")
                except Exception as e3:
                    logger.error(f"auto_match: 所有数据源加载失败: {e3}")
                    raise RuntimeError("无法加载岗位数据")

        # 逐岗匹配（批量模式：跳过逐岗位 LLM，用规则+图谱匹配，快百倍）
        results = []
        education_filtered = 0
        # 一次性提取简历技能（所有岗位共用）
        resume = await self.resume_repo.get_by_id(resume_id)
        if not resume:
            raise ResourceNotFoundError("简历不存在")
        resume_skills = [s.get("name", "") for s in (resume.skill_list or []) if s.get("name")]
        resume_skill_lower = {s.lower() for s in resume_skills}

        # 一次性预加载全部岗位的图谱技能树（单条批量查询），逐岗复用，
        # 避免批量循环里每岗位同步查 Neo4j 阻塞事件循环
        graph_ctx = await self._graph_skills_map({job["name"] for job in jobs if job.get("name")})

        for job in jobs:
            result = await self.do_match(
                user_id, resume_id, job, persist=False,
                _fast_match=True, _resume_ctx={"skills": resume_skills, "lower": resume_skill_lower, "exp": resume.work_experience_list or []},
                _graph_ctx=graph_ctx,
            )
            if result is None:
                education_filtered += 1
            else:
                results.append(result)

        # 按分数降序排列
        results.sort(key=lambda r: r["total_score"], reverse=True)

        # 分数 >= 50 过滤
        low_score_count = sum(1 for r in results if r["total_score"] < 50)
        results = [r for r in results if r["total_score"] >= 50]

        return {
            "results": results,
            "total_matched": len(jobs),
            "education_filtered": education_filtered,
            "score_filtered": low_score_count,
            "data_source": data_source,
        }

    async def get_result(self, resume_id: int, position_id: int) -> dict:
        """获取已有匹配结果"""
        result = await self.match_repo.get_by_ids(resume_id, position_id)
        if not result:
            raise ResourceNotFoundError("匹配结果不存在，请先执行匹配")
        return self._to_dict(result)

    async def get_history(self, user_id: int) -> list[dict]:
        """获取匹配历史"""
        results = await self.match_repo.get_history(user_id)
        return [self._to_dict(r) for r in results]

    def _to_dict(self, m) -> dict:
        """将 MatchResult 模型转为 API 返回格式"""
        return {
            "id": m.id,
            "resume_id": m.resume_id,
            "position_id": m.position_id,
            "position_name": m.position_name,
            "resume_name": m.resume_name,
            "total_score": m.total_score,
            "dimensions": m.dimensions or [],
            "gap_analysis": m.gap_analysis or {},
            "suggestions": m.suggestions or [],
            "match_date": str(m.match_date) if m.match_date else None,
        }
