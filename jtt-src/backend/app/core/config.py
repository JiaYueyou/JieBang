"""
全局配置 —— 从环境变量加载所有配置项。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv()

# 是否为测试模式
TESTING = os.getenv("TESTING", "false").lower() == "true"


def _required(name: str, test_default: str = "") -> str:
    """获取必需的环境变量，测试模式下使用默认值避免启动报错"""
    val = os.getenv(name, "")
    if not val:
        if TESTING:
            return test_default
        raise RuntimeError(f"缺少必需的环境变量: {name}")
    return val


# ===== MySQL 数据库 =====
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "jiebang_user")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ===== 爬虫数据库 jie_bang（只读）=====
RAW_DB_NAME = os.getenv("RAW_DB_NAME", "jie_bang")
RAW_DB_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{RAW_DB_NAME}"

# ===== Neo4j 知识图谱 =====
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# ===== JWT 认证 =====
JWT_SECRET_KEY = _required("JWT_SECRET_KEY", "test-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# ===== 大模型 API =====
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

# ===== Celery / Redis =====
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "true").lower() == "true"

# ===== ChromaDB =====
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "./data/chromadb")

# ===== 初始管理员 =====
INITIAL_ADMIN_ENABLED = os.getenv("INITIAL_ADMIN_ENABLED", "false").lower() == "true"
INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
