from celery import Celery

from app.config import settings


celery_app = Celery(
    "talentflow_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 900},
    result_backend_always_retry=True,
    result_backend_max_retries=3,
    result_backend_transport_options={
        "visibility_timeout": 900,
        "retry_policy": {"timeout": 5.0},
    },
    task_soft_time_limit=540,
    task_time_limit=600,
    result_expires=3600,
)
