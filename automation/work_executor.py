import logging
import os
import signal
import threading
import uuid

from sqlalchemy.orm import sessionmaker
from core.database import engine
from core.job_fence import fenced_job
from automation import work_ledger
from automation.celery_app import app

logger = logging.getLogger(__name__)


def _abort_child():
    # Only the prefork task process, never the API or Celery parent process.
    if os.getenv("ADMIRRA_WORKER_CHILD") == "1":
        os.kill(os.getpid(), signal.SIGTERM)
    else:
        logger.critical("Task lease lost outside a prefork child; commits remain fenced")


def execute_job(job_id, *, handler=None, abort=_abort_child):
    factory = sessionmaker(bind=engine)
    with factory.begin() as db:
        job = work_ledger.claim(db, uuid.UUID(str(job_id)))
    if job is None:
        return "not_claimed"
    stopped = threading.Event()
    lost = threading.Event()
    def keep_alive():
        while not stopped.wait(20):
            try:
                with factory.begin() as db:
                    alive = work_ledger.heartbeat(db, job["id"], job["lease_token"])
                if alive:
                    continue
            except Exception:
                logger.error("Execution heartbeat failed; aborting child")
            lost.set()
            abort()
            return
    heartbeat = threading.Thread(target=keep_alive, daemon=True, name="task-heartbeat")
    heartbeat.start()
    error = None
    try:
        if handler is None:
            from automation.work_handlers import run
            handler = run
        with fenced_job(job["id"], job["lease_token"]):
            handler(job["kind"], job["payload"])
    except BaseException as exc:
        error = exc
        logger.error("Job %s failed (%s)", job["id"], type(exc).__name__)
        if not isinstance(exc, Exception):
            raise
    finally:
        stopped.set()
        heartbeat.join(timeout=7)
    if lost.is_set():
        return "lease_lost"
    with factory.begin() as db:
        finished = work_ledger.finish(db, job["id"], job["lease_token"], error=error)
    return "finished" if finished else "lease_lost"


@app.task(name="admirra.execute")
def execute(job_id):
    return execute_job(job_id)
