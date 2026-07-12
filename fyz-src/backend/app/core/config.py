"""应用配置"""

import os
from dotenv import load_dotenv

load_dotenv()

TESTING = os.getenv("TESTING", "false").lower() == "true"


def _required_secret(name: str, *, test_default: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if TESTING and test_default is not None:
        return test_default
    raise RuntimeError(f"Required environment variable {name} is not configured")


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "jie_bang")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

# Initial administrator bootstrap
INITIAL_ADMIN_ENABLED = os.getenv(
    "INITIAL_ADMIN_ENABLED",
    "true" if TESTING else "false",
).lower() == "true"
INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

JWT_SECRET_KEY = _required_secret(
    "JWT_SECRET_KEY",
    test_default="test-only-jwt-secret-key",
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

# DeepSeek / Agent
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT_SECONDS = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "12"))

# Celery / Redis
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = (
    os.getenv(
        "CELERY_TASK_ALWAYS_EAGER",
        "true" if TESTING else "false",
    ).lower()
    == "true"
)

# Import files are restricted to this directory.
DATA_DIR = os.path.abspath(
    os.getenv(
        "DATA_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data"),
    )
)

# Private runtime storage. Files under this directory are never mounted as static assets.
LOCAL_STORAGE_PATH = os.path.abspath(
    os.getenv(
        "LOCAL_STORAGE_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "storage"),
    )
)
