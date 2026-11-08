from __future__ import annotations

import sys

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "smarttest",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=[
        "app.tasks.debug_tasks",
        "app.tasks.scan_tasks",
        "app.tasks.generation_tasks",
        "app.tasks.script_tasks",
        "app.tasks.execution_tasks",
        "app.tasks.failure_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_ignore_result=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_store_eager_result=False,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=3600,
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
    task_time_limit=900,
    task_soft_time_limit=840,
)

if sys.platform == "win32":
    # Celery's prefork pool is not supported on Windows. The worker command also
    # passes --pool=solo explicitly for clarity.
    celery_app.conf.worker_pool = "solo"
    celery_app.conf.worker_concurrency = 1

__all__ = ["celery_app"]
