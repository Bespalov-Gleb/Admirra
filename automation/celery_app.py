"""One transport task carrying a UUID; execution/result state lives in Postgres."""
import os
from celery import Celery, signals
from kombu import Queue
from core.runtime import env_bool, get_runtime

QUEUES = ("sync.manual", "sync.nightly", "reports", "maintenance", "ai.prewarm")


def make_app():
    url = os.getenv("CELERY_BROKER_URL", "")
    if not url:
        raise RuntimeError("CELERY_BROKER_URL is required; no implicit localhost broker")
    app = Celery("admirra", broker=url, include=["automation.work_executor"])
    app.conf.update(
        task_queues=[Queue(name) for name in QUEUES], task_default_queue="maintenance",
        task_create_missing_queues=False, task_serializer="json", accept_content=["json"],
        result_serializer="json", task_ignore_result=True, result_backend=None,
        task_acks_late=True, task_reject_on_worker_lost=True,
        task_acks_on_failure_or_timeout=True, worker_prefetch_multiplier=1,
        worker_cancel_long_running_tasks_on_connection_loss=True,
        task_soft_time_limit=3000, task_time_limit=3060, worker_max_tasks_per_child=50,
        worker_max_memory_per_child=512000, broker_connection_timeout=5,
        broker_connection_retry_on_startup=True, broker_pool_limit=5,
        task_publish_retry=False, enable_utc=True, timezone="UTC",
        broker_transport_options={"visibility_timeout": 3600, "socket_timeout": 5,
                                  "socket_connect_timeout": 5,
                                  "global_keyprefix": os.getenv("TASK_BROKER_PREFIX", "admirra:")},
        worker_send_task_events=True, task_send_sent_event=True,
    )
    return app


app = make_app()


@signals.worker_init.connect
def validate_worker(**_):
    if get_runtime().role != "worker" or not env_bool("DURABLE_TASKS", False):
        # Celery signals catch Exception, so startup rejection must be SystemExit.
        raise SystemExit("Celery workers require APP_PROCESS_ROLE=worker and DURABLE_TASKS=true")


@signals.worker_process_init.connect
def reset_connections_after_fork(**_):
    from core.database import engine
    engine.dispose(close=False)
    os.environ["ADMIRRA_WORKER_CHILD"] = "1"
