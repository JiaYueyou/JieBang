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
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_TIMEOUT_SECONDS = int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "60"))
DEEPSEEK_CONNECT_TIMEOUT_SECONDS = int(
    os.getenv("DEEPSEEK_CONNECT_TIMEOUT_SECONDS", "10")
)
DEEPSEEK_MAX_ATTEMPTS = max(
    1, min(4, int(os.getenv("DEEPSEEK_MAX_ATTEMPTS", "2")))
)
GRAPH_ENRICHMENT_TIMEOUT_SECONDS = max(
    DEEPSEEK_TIMEOUT_SECONDS,
    int(os.getenv("GRAPH_ENRICHMENT_TIMEOUT_SECONDS", "120")),
)
GRAPH_ENRICHMENT_MAX_ATTEMPTS = max(
    1, min(3, int(os.getenv("GRAPH_ENRICHMENT_MAX_ATTEMPTS", "2")))
)
GRAPH_ENRICHMENT_CONCURRENCY = max(
    1, min(8, int(os.getenv("GRAPH_ENRICHMENT_CONCURRENCY", "1" if TESTING else "2")))
)

# OpenAI-compatible embedding / retrieval
RETRIEVAL_EMBEDDING_PROVIDER = os.getenv(
    "RETRIEVAL_EMBEDDING_PROVIDER",
    "local_hash" if TESTING else "openai",
)
RETRIEVAL_VECTOR_BACKEND = os.getenv(
    "RETRIEVAL_VECTOR_BACKEND",
    "local_hash" if TESTING else "chroma",
)
RETRIEVAL_RELATIVE_SCORE_WINDOW = float(
    os.getenv("RETRIEVAL_RELATIVE_SCORE_WINDOW", "0.04")
)
if not 0 <= RETRIEVAL_RELATIVE_SCORE_WINDOW <= 1:
    raise RuntimeError(
        "RETRIEVAL_RELATIVE_SCORE_WINDOW must be between 0 and 1"
    )
RETRIEVAL_SEMANTIC_SCORE_FLOOR = float(
    os.getenv("RETRIEVAL_SEMANTIC_SCORE_FLOOR", "0.30")
)
if not 0 <= RETRIEVAL_SEMANTIC_SCORE_FLOOR <= 1:
    raise RuntimeError(
        "RETRIEVAL_SEMANTIC_SCORE_FLOOR must be between 0 and 1"
    )
OPENAI_EMBEDDING_API_KEY = os.getenv(
    "OPENAI_EMBEDDING_API_KEY",
    os.getenv("OPENAI_API_KEY", ""),
)
OPENAI_EMBEDDING_BASE_URL = os.getenv(
    "OPENAI_EMBEDDING_BASE_URL",
    "https://api.openai-proxy.org/v1",
)
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-large",
)
OPENAI_EMBEDDING_DIMENSIONS = int(
    os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "3072")
)
OPENAI_EMBEDDING_BATCH_SIZE = int(
    os.getenv("OPENAI_EMBEDDING_BATCH_SIZE", "64")
)
OPENAI_EMBEDDING_TIMEOUT_SECONDS = float(
    os.getenv("OPENAI_EMBEDDING_TIMEOUT_SECONDS", "60")
)

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

# Optional business cache. Keep this separate from the Celery broker/result
# databases. MySQL and Neo4j remain the sources of truth when Redis is down.
REDIS_CACHE_URL = os.getenv("REDIS_CACHE_URL", "redis://localhost:6379/3")
CACHE_ENABLED = (
    os.getenv("CACHE_ENABLED", "false" if TESTING else "true").lower() == "true"
)
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "jiebang:fyz:v1").strip(":")
CACHE_DEFAULT_TTL_SECONDS = max(
    1, int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "60"))
)
# CACHE_TASK_TTL_SECONDS is retained as a compatibility fallback for local
# environments created before active and terminal task TTLs were separated.
CACHE_TASK_TTL_SECONDS = max(
    1, int(os.getenv("CACHE_TASK_TTL_SECONDS", "3600"))
)
CACHE_TASK_ACTIVE_TTL_SECONDS = max(
    1, int(os.getenv("CACHE_TASK_ACTIVE_TTL_SECONDS", "15"))
)
CACHE_TASK_TERMINAL_TTL_SECONDS = max(
    1,
    int(
        os.getenv(
            "CACHE_TASK_TERMINAL_TTL_SECONDS",
            os.getenv("CACHE_TASK_TTL_SECONDS", "86400"),
        )
    ),
)
CACHE_CONNECT_TIMEOUT_SECONDS = max(
    0.05, float(os.getenv("CACHE_CONNECT_TIMEOUT_SECONDS", "0.5"))
)
CACHE_SOCKET_TIMEOUT_SECONDS = max(
    0.05, float(os.getenv("CACHE_SOCKET_TIMEOUT_SECONDS", "1.0"))
)

# Long-running data refresh.  Tests never start external crawlers.  In a
# deployed API process the scheduler is enabled by default and guarded by a
# database idempotency key, so multiple workers cannot execute the same slot.
AUTO_PIPELINE_ENABLED = (
    os.getenv("AUTO_PIPELINE_ENABLED", "false" if TESTING else "true").lower()
    == "true"
)
AUTO_PIPELINE_INTERVAL_MINUTES = max(
    15, int(os.getenv("AUTO_PIPELINE_INTERVAL_MINUTES", "1440"))
)
AUTO_PIPELINE_STARTUP_DELAY_SECONDS = max(
    0, int(os.getenv("AUTO_PIPELINE_STARTUP_DELAY_SECONDS", "60"))
)
AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS = max(
    60, int(os.getenv("AUTO_PIPELINE_SOURCE_TIMEOUT_SECONDS", "1800"))
)
AUTO_PIPELINE_SOURCE_IDS = tuple(
    int(value.strip())
    for value in os.getenv("AUTO_PIPELINE_SOURCE_IDS", "4,5,6").split(",")
    if value.strip().isdigit()
)
AUTO_PIPELINE_ENRICH_GRAPH = (
    os.getenv("AUTO_PIPELINE_ENRICH_GRAPH", "true").lower() == "true"
)
AUTO_PIPELINE_AUTO_PUBLISH_CONFIDENCE = min(
    1.0, max(0.0, float(os.getenv("AUTO_PIPELINE_AUTO_PUBLISH_CONFIDENCE", "0.90")))
)
AUTO_PIPELINE_BASELINE_LOOKBACK_MONTHS = max(
    6, int(os.getenv("AUTO_PIPELINE_BASELINE_LOOKBACK_MONTHS", "24"))
)
AUTO_PIPELINE_BASELINE_LAG_MONTHS = max(
    1, int(os.getenv("AUTO_PIPELINE_BASELINE_LAG_MONTHS", "2"))
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

CHROMA_MODE = os.getenv(
    "CHROMA_MODE",
    "ephemeral" if TESTING else "persistent",
)
CHROMA_PERSIST_PATH = os.path.abspath(
    os.getenv(
        "CHROMA_PERSIST_PATH",
        os.path.join(LOCAL_STORAGE_PATH, "chroma"),
    )
)
