"""Validated CLI; use this rather than an unguarded celery command."""
import sys
from core.runtime import env_bool, get_runtime


def main():
    if get_runtime().role != "worker" or not env_bool("DURABLE_TASKS", False):
        raise SystemExit("Requires worker role and DURABLE_TASKS=true")
    from automation.work_preflight import prepare_worker_parent
    prepare_worker_parent()
    from automation.celery_app import app
    app.worker_main(["worker", "--pool=prefork", "--loglevel=INFO", *sys.argv[1:]])


if __name__ == "__main__":
    main()
