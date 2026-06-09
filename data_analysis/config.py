"""全局配置"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR.parent / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"
SCRIPTS_DIR = ROOT_DIR / "scripts"

# 输入数据文件
DATA_FILES = [
    DATA_DIR / "jd_crawl_ifly.json",
    DATA_DIR / "jd_crawl_zl.json",
    DATA_DIR / "jd_crawl2.json",
]

# 去重：title+company 相似度阈值
DEDUP_THRESHOLD = 85

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 标准化输出字段
STANDARD_FIELDS = [
    "title", "company", "city", "salary", "experience", "education",
    "jd_text", "responsibilities", "requirements", "keywords",
    "posted_at", "url", "source", "crawled_at"
]

# 技能分类
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

# 预置技能词典（IT领域常见技能）
SKILL_DICT = {
    # 编程语言
    "Python": "programming_language",
    "Java": "programming_language",
    "JavaScript": "programming_language",
    "TypeScript": "programming_language",
    "C++": "programming_language",
    "C": "programming_language",
    "C#": "programming_language",
    "Go": "programming_language",
    "Rust": "programming_language",
    "Kotlin": "programming_language",
    "Swift": "programming_language",
    "Scala": "programming_language",
    "R": "programming_language",
    "MATLAB": "programming_language",
    "Shell": "programming_language",
    "PHP": "programming_language",
    "Ruby": "programming_language",
    "Perl": "programming_language",
    "SQL": "programming_language",
    "HTML": "programming_language",
    "CSS": "programming_language",
    "Dart": "programming_language",

    # 框架
    "Spring": "framework",
    "Spring Boot": "framework",
    "Spring Cloud": "framework",
    "SpringMVC": "framework",
    "MyBatis": "framework",
    "Hibernate": "framework",
    "Struts": "framework",
    "Django": "framework",
    "Flask": "framework",
    "FastAPI": "framework",
    "Tornado": "framework",
    "Vue": "framework",
    "React": "framework",
    "Angular": "framework",
    "Node.js": "framework",
    "Express": "framework",
    "Next.js": "framework",
    "Nuxt": "framework",
    "jQuery": "framework",
    "Bootstrap": "framework",
    "PyTorch": "framework",
    "TensorFlow": "framework",
    "Keras": "framework",
    "Scikit-learn": "framework",
    "Pandas": "framework",
    "NumPy": "framework",
    "LangChain": "framework",
    "LangGraph": "framework",

    # 工具/平台
    "Docker": "tool",
    "Kubernetes": "tool",
    "Git": "tool",
    "Jenkins": "tool",
    "Maven": "tool",
    "Gradle": "tool",
    "Nginx": "tool",
    "Apache": "tool",
    "Tomcat": "tool",
    "Linux": "tool",
    "JIRA": "tool",
    "Confluence": "tool",
    "CI/CD": "tool",
    "Ansible": "tool",
    "Terraform": "tool",
    "ELK": "tool",
    "Prometheus": "tool",
    "Grafana": "tool",
    "Zabbix": "tool",
    "Webpack": "tool",
    "Vite": "tool",
    "Postman": "tool",
    "Swagger": "tool",
    "Figma": "tool",
    "VS Code": "tool",
    "IntelliJ IDEA": "tool",
    "PyCharm": "tool",
    "Eclipse": "tool",

    # 数据库
    "MySQL": "database",
    "PostgreSQL": "database",
    "Oracle": "database",
    "SQL Server": "database",
    "MongoDB": "database",
    "Redis": "database",
    "Elasticsearch": "database",
    "SQLite": "database",
    "Cassandra": "database",
    "Neo4j": "database",
    "HBase": "database",
    "Hive": "database",
    "InfluxDB": "database",
    "达梦": "database",
    "人大金仓": "database",
    "Milvus": "database",
    "ChromaDB": "database",

    # 云计算
    "AWS": "cloud",
    "Azure": "cloud",
    "阿里云": "cloud",
    "腾讯云": "cloud",
    "华为云": "cloud",
    "微服务": "cloud",
    "Serverless": "cloud",
    "DevOps": "cloud",
    "云原生": "cloud",

    # AI/机器学习
    "机器学习": "ai_ml",
    "深度学习": "ai_ml",
    "自然语言处理": "ai_ml",
    "NLP": "ai_ml",
    "计算机视觉": "ai_ml",
    "CV": "ai_ml",
    "大模型": "ai_ml",
    "LLM": "ai_ml",
    "RAG": "ai_ml",
    "神经网络": "ai_ml",
    "推荐系统": "ai_ml",
    "数据挖掘": "ai_ml",
    "数据科学": "ai_ml",
    "语音识别": "ai_ml",
    "知识图谱": "ai_ml",
    "联邦学习": "ai_ml",
    "强化学习": "ai_ml",

    # 领域知识
    "物联网": "domain_knowledge",
    "IoT": "domain_knowledge",
    "嵌入式": "domain_knowledge",
    "FPGA": "domain_knowledge",
    "区块链": "domain_knowledge",
    "自动驾驶": "domain_knowledge",
    "ROS": "domain_knowledge",
    "网络安全": "domain_knowledge",
    "大数据": "domain_knowledge",
    "Hadoop": "domain_knowledge",
    "Spark": "domain_knowledge",
    "Flink": "domain_knowledge",
    "Kafka": "domain_knowledge",
    "RabbitMQ": "domain_knowledge",
    "ZooKeeper": "domain_knowledge",
    "Dubbo": "domain_knowledge",
    "gRPC": "domain_knowledge",
    "RESTful API": "domain_knowledge",
    "GraphQL": "domain_knowledge",
    "WebSocket": "domain_knowledge",

    # 软技能
    "团队管理": "soft_skill",
    "项目管理": "soft_skill",
    "沟通能力": "soft_skill",
    "需求分析": "soft_skill",
    "技术文档": "soft_skill",
}

# 岗位名标准化规则
TITLE_NORMALIZE_PATTERNS = [
    # 去除括号内容
    (r'[（(][^)）]*[)）]', ''),
    # 去除校招/实习/应届标记
    (r'[\[【]?(?:校招|实习|应届|社招|线上面)[\]】]?', ''),
    # 去除地点后缀
    (r'[-－—]\s*(?:北京|上海|广州|深圳|杭州|成都|武汉|南京|西安|合肥|苏州|长沙)', ''),
    # 去除薪资/加班/福利描述
    (r'[\[【]?(?:高薪|急[招聘]|双休|五险一金|包吃住|远程|居家|线上面试|\d+K|\d+薪)[\]】]?', ''),
]
