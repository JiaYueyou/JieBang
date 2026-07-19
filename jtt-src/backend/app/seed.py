"""
数据库初始化脚本 —— 首次启动时自动填充种子数据（岗位、技能、简历、学习路径、收藏）。
幂等操作：仅在对应表为空时才插入数据。
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.models.position import JobPosition, Skill, SkillChange
from app.models.resume import Resume
from app.models.learning import LearningPath
from app.models.favorite import Favorite

# ===== 岗位种子数据 =====
POSITIONS = [
    # -- 新兴岗位 --
    {
        "name": "AI 智能体开发工程师", "category": "new",
        "aliases": ["Agent开发工程师", "大模型Agent工程师"],
        "summary": "负责基于大语言模型构建、部署和优化 AI 智能体（Agent）系统，涵盖工具调用、多步推理和自主决策能力。",
        "responsibilities": [
            "设计并实现 LLM-based Agent 架构，包括 ReAct、Plan-and-Solve 等范式",
            "构建 Agent 工具链（Tool Use / Function Calling）与记忆系统",
            "开发 Multi-Agent 协作框架，实现复杂任务的自动分解与协同",
            "持续跟踪 Agent 框架（LangGraph、AutoGen、CrewAI）的最新进展并评估集成",
        ],
        "industry_scenarios": ["智能客服系统", "自动化运维Agent", "个人AI助理", "企业知识管理"],
        "tech_stack": ["AI框架", "编程语言", "AI技术", "数据存储", "后端开发"],
        "career_level": "mid", "salary_range": "25K-50K",
        "required_skills": [
            {"name": "Python", "level": "required", "category": "编程语言"},
            {"name": "LangChain / LangGraph", "level": "required", "category": "AI框架"},
            {"name": "LLM API 调用与调优", "level": "required", "category": "AI技术"},
            {"name": "Prompt Engineering", "level": "required", "category": "AI技术"},
            {"name": "RAG 检索增强生成", "level": "required", "category": "AI技术"},
        ],
        "preferred_skills": [
            {"name": "Multi-Agent 系统设计", "level": "preferred", "category": "AI框架"},
            {"name": "向量数据库（Milvus/ChromaDB）", "level": "preferred", "category": "数据存储"},
            {"name": "FastAPI / Flask", "level": "preferred", "category": "后端开发"},
        ],
        "skill_changes": [],
    },
    {
        "name": "上下文工程专家", "category": "new",
        "aliases": ["Context Engineering Specialist", "上下文优化工程师"],
        "summary": "专注于 LLM 应用中的上下文管理策略，包括上下文窗口优化、记忆管理和信息检索策略设计。",
        "responsibilities": [
            "设计 LLM 应用的上下文管理架构，优化 token 利用率",
            "开发上下文压缩与信息蒸馏技术，提升长对话场景下的模型表现",
            "构建动态上下文注入策略，结合实时数据与历史对话",
        ],
        "industry_scenarios": ["AI 产品公司", "大模型中间件", "对话系统优化"],
        "tech_stack": ["AI技术", "编程语言", "AI框架"],
        "career_level": "senior", "salary_range": "30K-60K",
        "required_skills": [
            {"name": "Prompt Engineering", "level": "required", "category": "AI技术"},
            {"name": "LLM 推理与 Token 优化", "level": "required", "category": "AI技术"},
            {"name": "Python", "level": "required", "category": "编程语言"},
        ],
        "preferred_skills": [
            {"name": "Agent 框架", "level": "preferred", "category": "AI框架"},
            {"name": "NLP 基础", "level": "preferred", "category": "AI技术"},
        ],
        "skill_changes": [],
    },
    {
        "name": "具身智能算法工程师", "category": "new",
        "aliases": ["Embodied AI Engineer", "机器人算法工程师"],
        "summary": "研发具身智能系统，将大模型与机器人控制相结合，实现感知-决策-执行的闭环。",
        "responsibilities": [
            "研发机器人视觉感知与操作规划算法",
            "结合 VLM（视觉语言模型）实现机器人自主决策",
            "构建仿真环境（Isaac Sim）中的训练流程",
        ],
        "industry_scenarios": ["工业机器人", "服务机器人", "自动驾驶", "仓储物流"],
        "tech_stack": ["编程语言", "机器人框架", "AI技术", "仿真平台"],
        "career_level": "senior", "salary_range": "35K-70K",
        "required_skills": [
            {"name": "Python / C++", "level": "required", "category": "编程语言"},
            {"name": "ROS / ROS2", "level": "required", "category": "机器人框架"},
            {"name": "计算机视觉", "level": "required", "category": "AI技术"},
            {"name": "深度强化学习", "level": "required", "category": "AI技术"},
        ],
        "preferred_skills": [
            {"name": "NVIDIA Isaac Sim", "level": "preferred", "category": "仿真平台"},
            {"name": "VLM 模型微调", "level": "preferred", "category": "AI技术"},
        ],
        "skill_changes": [],
    },
    # -- 既有岗位 --
    {
        "name": "Java 开发工程师", "category": "existing",
        "aliases": ["Java工程师", "Java开发", "Java后端"],
        "summary": "负责企业级后端系统设计与开发，当前趋势要求具备分布式、云原生和 AI 集成能力。",
        "responsibilities": [
            "参与系统架构设计，编写高质量 Java 代码",
            "负责微服务架构的设计与治理",
            "参与 AI 能力的后端集成（如 RAG 接口、Agent 调用）",
            "持续优化系统性能与可观测性",
        ],
        "industry_scenarios": ["金融科技", "电商平台", "企业SaaS", "互联网"],
        "tech_stack": ["编程语言", "数据存储", "架构设计", "云原生", "AI集成", "前端"],
        "career_level": "mid", "salary_range": "15K-35K",
        "required_skills": [
            {"name": "Java / Spring Boot", "level": "required", "category": "编程语言"},
            {"name": "MySQL / Redis", "level": "required", "category": "数据存储"},
            {"name": "微服务架构", "level": "required", "category": "架构设计"},
            {"name": "Docker / K8s", "level": "required", "category": "云原生"},
            {"name": "LLM API 集成", "level": "required", "category": "AI集成"},
        ],
        "preferred_skills": [
            {"name": "智能体开发", "level": "preferred", "category": "AI集成"},
            {"name": "全栈能力（Vue/React）", "level": "preferred", "category": "前端"},
            {"name": "RAG 框架", "level": "preferred", "category": "AI集成"},
        ],
        "skill_changes": [
            {"skill_name": "智能体开发", "change_type": "added", "change_date": "2026-02",
             "description": "Java工程师需要了解 Agent 开发框架，能够将 AI Agent 集成到业务系统", "source": "招聘平台+行业报告"},
            {"skill_name": "LLM API 集成", "change_type": "added", "change_date": "2025-09",
             "description": "大模型能力成为后端基础设施，需要掌握 LLM API 调用与编排", "source": "技术博客+JD分析"},
            {"skill_name": "SSH/SSM 框架", "change_type": "removed", "change_date": "2025-06",
             "description": "传统框架逐步被 Spring Boot 和微服务替代，招聘需求显著下降", "source": "招聘数据趋势"},
            {"skill_name": "RAG 框架", "change_type": "added", "change_date": "2026-04",
             "description": "检索增强生成成为企业知识库场景的核心技术", "source": "行业技术报告"},
        ],
    },
    {
        "name": "前端开发工程师", "category": "existing",
        "aliases": ["前端工程师", "Web前端", "H5开发"],
        "summary": "负责 Web 前端架构与开发，当前趋势涵盖 AI 辅助开发工具集成和跨端开发能力。",
        "responsibilities": [
            "负责产品前端架构设计与核心模块开发",
            "优化首屏加载性能与运行时体验",
            "使用 AI 辅助工具（Copilot / Cursor）提升开发效率",
        ],
        "industry_scenarios": ["互联网产品", "企业后台", "数据可视化", "移动端H5"],
        "tech_stack": ["编程语言", "前端框架", "构建工具", "AI工具", "全栈", "数据可视化"],
        "career_level": "mid", "salary_range": "15K-30K",
        "required_skills": [
            {"name": "TypeScript", "level": "required", "category": "编程语言"},
            {"name": "Vue 3 / React", "level": "required", "category": "前端框架"},
            {"name": "Vite / Webpack", "level": "required", "category": "构建工具"},
            {"name": "AI 辅助开发工具", "level": "required", "category": "AI工具"},
        ],
        "preferred_skills": [
            {"name": "Node.js / SSR", "level": "preferred", "category": "全栈"},
            {"name": "可视化（G6/ECharts）", "level": "preferred", "category": "数据可视化"},
        ],
        "skill_changes": [
            {"skill_name": "AI 辅助开发工具", "change_type": "added", "change_date": "2025-12",
             "description": "Copilot/Cursor 等工具已成为前端必备用具", "source": "技术社区调查"},
            {"skill_name": "TypeScript", "change_type": "modified", "change_date": "2025-06",
             "description": "从'加分项'升级为'必备技能'", "source": "JD分析趋势"},
        ],
    },
    {
        "name": "数据工程师", "category": "existing",
        "aliases": ["大数据工程师", "Data Engineer"],
        "summary": "负责数据平台建设与数据管道开发，当前趋势要求融合 AI/ML 工程化能力。",
        "responsibilities": [
            "构建和维护大规模数据处理管道（ETL/ELT）",
            "设计数据仓库与数据湖架构",
            "支撑 AI 模型的训练数据准备与特征工程",
        ],
        "industry_scenarios": ["互联网数据平台", "金融风控", "AI 数据中台"],
        "tech_stack": ["编程语言", "大数据框架", "数据架构", "AI工程化"],
        "career_level": "mid", "salary_range": "20K-40K",
        "required_skills": [
            {"name": "Python / SQL", "level": "required", "category": "编程语言"},
            {"name": "Spark / Flink", "level": "required", "category": "大数据框架"},
            {"name": "数据仓库建模", "level": "required", "category": "数据架构"},
        ],
        "preferred_skills": [
            {"name": "ML Pipeline", "level": "preferred", "category": "AI工程化"},
            {"name": "实时计算", "level": "preferred", "category": "大数据框架"},
        ],
        "skill_changes": [
            {"skill_name": "ML Pipeline", "change_type": "added", "change_date": "2026-01",
             "description": "数据工程与 AI 工程化边界模糊，需要掌握 ML 训练管线", "source": "技术大会分享"},
        ],
    },
]

# ===== 简历种子数据（关联 admin user_id=1）=====
RESUMES = [
    {
        "name": "Java后端开发简历",
        "target_position": "Java 开发工程师",
        "personal_name": "张三", "personal_email": "zhangsan@example.com",
        "personal_phone": "138****1234", "personal_location": "北京",
        "desired_position": "Java 开发工程师", "desired_city": "北京",
        "salary_expectation": "15K-25K", "work_mode": "fulltime",
        "education_list": [
            {"school": "某科技大学", "degree": "本科", "major": "计算机科学与技术",
             "startDate": "2019-09", "endDate": "2023-06"},
        ],
        "work_experience_list": [
            {"company": "某互联网公司", "position": "Java 后端开发",
             "startDate": "2023-07", "endDate": "2026-06",
             "description": "负责电商平台订单系统后端开发，使用 Spring Boot + MySQL + Redis 技术栈，参与微服务拆分与容器化部署。",
             "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Docker"]},
        ],
        "project_list": [
            {"name": "电商订单系统", "role": "核心开发",
             "description": "负责订单模块的设计与开发，日均处理订单量 10万+，采用微服务架构。",
             "technologies": ["Java", "Spring Cloud", "RocketMQ", "MySQL"],
             "highlights": ["系统QPS从500优化至2000", "引入消息队列解耦订单流程"]},
        ],
        "skill_list": [
            {"id": "rs1", "name": "Java", "level": "advanced", "category": "编程语言"},
            {"id": "rs2", "name": "Spring Boot", "level": "advanced", "category": "框架"},
            {"id": "rs3", "name": "MySQL", "level": "required", "category": "数据存储"},
            {"id": "rs4", "name": "Redis", "level": "required", "category": "数据存储"},
            {"id": "rs5", "name": "Docker", "level": "preferred", "category": "云原生"},
            {"id": "rs6", "name": "微服务", "level": "preferred", "category": "架构"},
        ],
        "self_evaluation": "三年Java后端开发经验，熟悉企业级应用开发，具备良好的系统设计能力和团队协作精神。",
    },
    {
        "name": "AI方向简历",
        "target_position": "AI 智能体开发工程师",
        "personal_name": "李四", "personal_email": "lisi@example.com",
        "personal_phone": "139****5678", "personal_location": "上海",
        "desired_position": "AI 工程师", "desired_city": "上海",
        "salary_expectation": "25K-40K", "work_mode": "fulltime",
        "education_list": [
            {"school": "某理工大学", "degree": "硕士", "major": "人工智能",
             "startDate": "2021-09", "endDate": "2024-06"},
        ],
        "work_experience_list": [
            {"company": "某AI公司", "position": "AI 算法工程师",
             "startDate": "2024-07", "endDate": "2026-05",
             "description": "负责基于 LLM 的对话系统开发，使用 LangChain + FastAPI 构建 RAG 问答系统，参与 Agent 框架预研。",
             "skills": ["Python", "LangChain", "FastAPI", "向量数据库"]},
        ],
        "project_list": [
            {"name": "企业智能知识库", "role": "项目负责人",
             "description": "搭建基于 RAG 的企业级智能问答系统，支持多文档格式解析与检索。",
             "technologies": ["Python", "LangChain", "ChromaDB", "FastAPI", "Vue 3"],
             "highlights": ["检索召回率 95%+", "日均问答量 5000+"]},
        ],
        "skill_list": [
            {"id": "rs10", "name": "Python", "level": "advanced", "category": "编程语言"},
            {"id": "rs11", "name": "LangChain", "level": "required", "category": "AI框架"},
            {"id": "rs12", "name": "LLM API", "level": "required", "category": "AI技术"},
            {"id": "rs13", "name": "RAG", "level": "required", "category": "AI技术"},
            {"id": "rs14", "name": "Prompt Engineering", "level": "required", "category": "AI技术"},
            {"id": "rs15", "name": "FastAPI", "level": "preferred", "category": "后端"},
        ],
        "self_evaluation": "对 AI Agent 和 RAG 方向有浓厚兴趣，持续跟踪前沿技术，具备独立项目交付能力。",
    },
]

# ===== 学习路径种子数据 =====
LEARNING_PATHS = [
    {
        "name": "Java工程师进阶路径",
        "position_name": "Java 开发工程师",
        "total_duration": "12周",
        "steps": [
            {"id": "s-1", "order": 1, "title": "Java 核心基础强化",
             "description": "深入理解 Java 集合框架、JVM 内存模型、并发编程",
             "duration": "1-2周", "completed": True,
             "resources": [
                 {"id": "res-1", "title": "《深入理解Java虚拟机》", "type": "book", "url": "", "platform": "京东读书"},
                 {"id": "res-2", "title": "Java并发编程实战", "type": "course", "url": "", "platform": "慕课网"},
             ]},
            {"id": "s-2", "order": 2, "title": "Spring Boot 微服务实战",
             "description": "掌握 Spring Cloud、服务注册与发现、网关、配置中心",
             "duration": "3-5周", "completed": False,
             "resources": [
                 {"id": "res-3", "title": "Spring Cloud 微服务实战", "type": "project", "url": "", "platform": "GitHub"},
                 {"id": "res-4", "title": "微服务架构设计模式", "type": "book", "url": "", "platform": "异步社区"},
             ]},
            {"id": "s-3", "order": 3, "title": "Docker & Kubernetes",
             "description": "容器化部署、K8s基础操作、Helm Charts",
             "duration": "6-7周", "completed": False,
             "resources": [
                 {"id": "res-5", "title": "Kubernetes 入门到实践", "type": "course", "url": "", "platform": "阿里云大学"},
             ]},
            {"id": "s-4", "order": 4, "title": "LLM API 集成与 Agent 开发",
             "description": "学习大模型 API 调用范式、RAG 系统搭建、LangChain 基础",
             "duration": "8-10周", "completed": False,
             "resources": [
                 {"id": "res-6", "title": "LangChain 实战指南", "type": "article", "url": "", "platform": "掘金"},
                 {"id": "res-7", "title": "RAG 从零到一", "type": "video", "url": "", "platform": "B站"},
             ]},
            {"id": "s-5", "order": 5, "title": "综合实战项目",
             "description": "使用 Java + Spring Boot + LLM 构建智能后端系统",
             "duration": "11-12周", "completed": False,
             "resources": [
                 {"id": "res-8", "title": "AI-Native 应用开发指南", "type": "article", "url": "", "platform": "知乎专栏"},
             ]},
        ],
    },
    {
        "name": "AI智能体开发学习路径",
        "position_name": "AI 智能体开发工程师",
        "total_duration": "10周",
        "steps": [
            {"id": "s2-1", "order": 1, "title": "Python 高级编程",
             "description": "异步编程、装饰器、类型注解、性能优化",
             "duration": "1-2周", "completed": False,
             "resources": [
                 {"id": "res2-1", "title": "Fluent Python（第二版）", "type": "book", "url": "", "platform": "O'Reilly"},
             ]},
            {"id": "s2-2", "order": 2, "title": "LLM 基础与 Prompt Engineering",
             "description": "理解 LLM 工作原理、掌握提示工程方法论",
             "duration": "3-4周", "completed": False,
             "resources": [
                 {"id": "res2-2", "title": "Prompt Engineering Guide", "type": "course", "url": "", "platform": "DeepLearning.AI"},
             ]},
            {"id": "s2-3", "order": 3, "title": "LangChain & Agent 框架",
             "description": "掌握 LangChain/LangGraph、ReAct 模式、Tool Calling",
             "duration": "5-7周", "completed": False,
             "resources": [
                 {"id": "res2-3", "title": "LangChain: Chat with Your Data", "type": "course", "url": "", "platform": "DeepLearning.AI"},
                 {"id": "res2-4", "title": "Building Agentic Applications", "type": "video", "url": "", "platform": "YouTube"},
             ]},
            {"id": "s2-4", "order": 4, "title": "RAG 与向量数据库",
             "description": "搭建企业级 RAG 系统、ChromaDB/Milvus 实践",
             "duration": "8-9周", "completed": False,
             "resources": [
                 {"id": "res2-5", "title": "向量数据库实战", "type": "project", "url": "", "platform": "GitHub"},
             ]},
            {"id": "s2-5", "order": 5, "title": "Multi-Agent 系统实战",
             "description": "构建多Agent协作系统，完成端到端项目",
             "duration": "10周", "completed": False,
             "resources": [
                 {"id": "res2-6", "title": "AutoGen 实战教程", "type": "article", "url": "", "platform": "微软官方"},
             ]},
        ],
    },
]


async def seed_all():
    """主入口：按顺序填充所有种子数据（如已存在则跳过）"""
    async with async_session() as db:
        await _seed_positions(db)
        await _seed_resumes(db)
        await _seed_learning_paths(db)
        await _seed_favorites(db)
        await db.commit()


async def _seed_positions(db: AsyncSession):
    """种子：岗位 + 技能 + 技能变化"""
    from sqlalchemy import select, func
    result = await db.execute(select(func.count()).select_from(JobPosition))
    if result.scalar() > 0:
        return

    for pdata in POSITIONS:
        pos = JobPosition(
            name=pdata["name"], category=pdata["category"],
            aliases=pdata["aliases"], summary=pdata["summary"],
            responsibilities=pdata["responsibilities"],
            industry_scenarios=pdata["industry_scenarios"],
            tech_stack=pdata["tech_stack"],
            career_level=pdata["career_level"], salary_range=pdata["salary_range"],
        )
        db.add(pos)
        await db.flush()  # 获取 pos.id

        # 添加技能
        for sk in pdata["required_skills"]:
            db.add(Skill(position_id=pos.id, name=sk["name"], level=sk["level"],
                         kind="required", category=sk["category"]))
        for sk in pdata["preferred_skills"]:
            db.add(Skill(position_id=pos.id, name=sk["name"], level=sk["level"],
                         kind="preferred", category=sk["category"]))

        # 添加技能变化（仅既有岗位）
        for sc in pdata["skill_changes"]:
            db.add(SkillChange(position_id=pos.id, skill_name=sc["skill_name"],
                               change_type=sc["change_type"], description=sc["description"],
                               source=sc["source"], change_date=sc["change_date"]))


async def _seed_resumes(db: AsyncSession):
    """种子：示例简历（关联 admin 用户）"""
    from sqlalchemy import select, func
    result = await db.execute(select(func.count()).select_from(Resume))
    if result.scalar() > 0:
        return

    for rdata in RESUMES:
        resume = Resume(
            user_id=1,
            name=rdata["name"], target_position=rdata["target_position"],
            personal_name=rdata["personal_name"], personal_email=rdata["personal_email"],
            personal_phone=rdata["personal_phone"], personal_location=rdata["personal_location"],
            desired_position=rdata["desired_position"], desired_city=rdata["desired_city"],
            salary_expectation=rdata["salary_expectation"], work_mode=rdata["work_mode"],
            education_list=rdata["education_list"],
            work_experience_list=rdata["work_experience_list"],
            project_list=rdata["project_list"],
            skill_list=rdata["skill_list"],
            self_evaluation=rdata["self_evaluation"],
        )
        db.add(resume)


async def _seed_learning_paths(db: AsyncSession):
    """种子：学习路径（查找实际岗位 ID）"""
    from sqlalchemy import select, func
    result = await db.execute(select(func.count()).select_from(LearningPath))
    if result.scalar() > 0:
        return

    for lp in LEARNING_PATHS:
        # 查找对应岗位的实际 ID
        pos_result = await db.execute(
            select(JobPosition.id).where(JobPosition.name == lp["position_name"])
        )
        pos_id = pos_result.scalar()
        if pos_id is None:
            continue

        path = LearningPath(
            user_id=1, name=lp["name"],
            position_id=pos_id, position_name=lp["position_name"],
            steps=lp["steps"], total_duration=lp["total_duration"],
        )
        db.add(path)


async def _seed_favorites(db: AsyncSession):
    """种子：示例收藏（岗位、学习资料、错题）"""
    from sqlalchemy import select, func
    result = await db.execute(select(func.count()).select_from(Favorite))
    if result.scalar() > 0:
        return

    # 查找岗位 ID
    java_result = await db.execute(
        select(JobPosition).where(JobPosition.name == "Java 开发工程师")
    )
    ai_result = await db.execute(
        select(JobPosition).where(JobPosition.name == "AI 智能体开发工程师")
    )
    java_pos = java_result.scalar()
    ai_pos = ai_result.scalar()

    # 收藏岗位
    if java_pos:
        db.add(Favorite(
            user_id=1, item_type="position", item_id=str(java_pos.id),
            title=java_pos.name,
            summary=java_pos.summary[:100] if java_pos.summary else "",
            item_data={
                "position_id": java_pos.id, "name": java_pos.name,
                "category": java_pos.category, "career_level": java_pos.career_level,
                "salary_range": java_pos.salary_range,
                "skills": ["Java / Spring Boot", "MySQL / Redis", "微服务架构", "Docker / K8s"],
            },
        ))
    if ai_pos:
        db.add(Favorite(
            user_id=1, item_type="position", item_id=str(ai_pos.id),
            title=ai_pos.name,
            summary=ai_pos.summary[:100] if ai_pos.summary else "",
            item_data={
                "position_id": ai_pos.id, "name": ai_pos.name,
                "category": ai_pos.category, "career_level": ai_pos.career_level,
                "salary_range": ai_pos.salary_range,
                "skills": ["Python", "LangChain", "LLM API", "RAG", "Prompt Engineering"],
            },
        ))

    # 收藏学习资料
    db.add(Favorite(
        user_id=1, item_type="learning_resource", item_id="res-1",
        title="《深入理解Java虚拟机》",
        summary="Java性能调优必读经典",
        item_data={
            "resource_id": "res-1", "title": "《深入理解Java虚拟机》",
            "type": "book", "url": "", "platform": "京东读书",
            "skill_tags": ["Java", "JVM"],
        },
    ))

    # 收藏错题
    db.add(Favorite(
        user_id=1, item_type="quiz_error", item_id="quiz-1",
        title="Java GC 算法选择",
        summary="关于 CMS 和 G1 收集器的适用场景",
        item_data={
            "quiz_id": "quiz-1", "step_id": "s-1",
            "question": "在堆内存 4GB 以上时，JDK 9+ 默认使用哪个垃圾收集器？",
            "user_answer": "CMS", "correct_answer": "G1",
            "explanation": "JDK 9 开始 G1 成为默认垃圾收集器，适合大内存场景。",
            "skill_name": "Java",
        },
    ))
