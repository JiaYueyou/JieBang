"""Celery application configuration."""

import os

from celery import Celery

from app.core.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_TASK_ALWAYS_EAGER,
)

celery_app = Celery(
    "jiebang",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.skill_import", "app.tasks.graph_sync", "app.tasks.cache_warmup",
    ],
)
celery_app.conf.update(
    task_always_eager=CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "cache.warm_popular_queries": {"queue": "cache_warmup"},
    },
    beat_schedule={
        "warm-popular-fyz-queries": {
            "task": "cache.warm_popular_queries",
            "schedule": max(
                60.0,
                float(os.getenv("CACHE_WARM_INTERVAL_SECONDS", "60")),
            ),
            "options": {"queue": "cache_warmup", "expires": 55},
        },
    },
)
