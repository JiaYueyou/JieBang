"""IT 技能标准词典与别名。"""

SKILL_CATEGORIES = {
    "programming_language": "编程语言",
    "framework": "框架",
    "tool": "工具/平台",
    "database": "数据库",
    "cloud": "云计算",
    "ai_ml": "AI/机器学习",
    "domain_knowledge": "领域知识",
    "soft_skill": "软技能",
}

_GROUPS = {
    "programming_language": [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C", "C#",
        "Go", "Rust", "Kotlin", "Swift", "Scala", "R", "MATLAB", "Shell",
        "PHP", "Ruby", "Perl", "SQL", "HTML", "CSS", "Dart",
    ],
    "framework": [
        "Spring", "Spring Boot", "Spring Cloud", "SpringMVC", "MyBatis",
        "Hibernate", "Struts", "Django", "Flask", "FastAPI", "Tornado",
        "Vue", "React", "Angular", "Node.js", "Express", "Next.js", "Nuxt",
        "jQuery", "Bootstrap", "PyTorch", "TensorFlow", "Keras",
        "Scikit-learn", "Pandas", "NumPy", "LangChain", "LangGraph",
    ],
    "tool": [
        "Docker", "Kubernetes", "Git", "Jenkins", "Maven", "Gradle", "Nginx",
        "Apache", "Tomcat", "Linux", "JIRA", "Confluence", "CI/CD", "Ansible",
        "Terraform", "ELK", "Prometheus", "Grafana", "Zabbix", "Webpack",
        "Vite", "Postman", "Swagger", "Figma", "VS Code", "IntelliJ IDEA",
        "PyCharm", "Eclipse",
    ],
    "database": [
        "MySQL", "PostgreSQL", "Oracle", "SQL Server", "MongoDB", "Redis",
        "Elasticsearch", "SQLite", "Cassandra", "Neo4j", "HBase", "Hive",
        "InfluxDB", "达梦", "人大金仓", "Milvus", "ChromaDB",
    ],
    "cloud": [
        "AWS", "Azure", "阿里云", "腾讯云", "华为云", "微服务", "Serverless",
        "DevOps", "云原生",
    ],
    "ai_ml": [
        "机器学习", "深度学习", "自然语言处理", "NLP", "计算机视觉", "CV",
        "大模型", "LLM", "RAG", "神经网络", "推荐系统", "数据挖掘",
        "数据科学", "语音识别", "知识图谱", "联邦学习", "强化学习",
    ],
    "domain_knowledge": [
        "物联网", "IoT", "嵌入式", "FPGA", "区块链", "自动驾驶", "ROS",
        "网络安全", "大数据", "Hadoop", "Spark", "Flink", "Kafka",
        "RabbitMQ", "ZooKeeper", "Dubbo", "gRPC", "RESTful API", "GraphQL",
        "WebSocket",
    ],
    "soft_skill": ["团队管理", "项目管理", "沟通能力", "需求分析", "技术文档"],
}

SKILL_DICT = {
    name: category
    for category, names in _GROUPS.items()
    for name in names
}
_SKILL_NAMES_CASEFOLD = {name.casefold(): name for name in SKILL_DICT}

SKILL_ALIASES = {
    # ── 大小写别名 ──
    "k8s": "Kubernetes",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "es": "Elasticsearch",
    "elastic search": "Elasticsearch",
    "js": "JavaScript",
    "ts": "TypeScript",
    "nodejs": "Node.js",
    "vue3": "Vue",
    "vue.js": "Vue",
    "react.js": "React",
    "sklearn": "Scikit-learn",
    "cicd": "CI/CD",
    "ci/cd": "CI/CD",
    "golang": "Go",
    "mongo": "MongoDB",
    "zk": "ZooKeeper",
    # ── 来自 data_analysis 的补充别名 ──
    ".net": "C#",
    "node": "Node.js",
    "pytorch": "PyTorch",
    "tf": "TensorFlow",
    "es6": "JavaScript",
}


def canonical_key(name: str) -> str:
    normalized = name.strip().casefold()
    special = {
        "c++": "cpp",
        "c#": "csharp",
        "ci/cd": "cicd",
        "node.js": "nodejs",
        "next.js": "nextjs",
    }
    if normalized in special:
        return special[normalized]
    return "".join(character for character in normalized if character.isalnum())


def normalize_skill(name: str) -> tuple[str, str] | None:
    stripped = name.strip()
    lookup_key = stripped.casefold()
    canonical = SKILL_ALIASES.get(
        lookup_key,
        _SKILL_NAMES_CASEFOLD.get(lookup_key, stripped),
    )
    category = SKILL_DICT.get(canonical)
    return (canonical, category) if category else None
