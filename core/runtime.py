"""Explicit process capabilities; no imports with DB/application side effects.

The legacy default preserves current deployment until an explicit cutover.
"""
from dataclasses import dataclass
import os
from typing import Mapping


def env_bool(name: str, default: bool, env: Mapping[str, str] | None = None) -> bool:
    values = os.environ if env is None else env
    raw = values.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def env_int(name: str, default: int, minimum: int = 0, maximum: int = 10000) -> int:
    value = int(os.getenv(name, str(default)))
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True)
class Runtime:
    role: str
    auto_bootstrap: bool
    sync_worker: bool
    api_scheduler: bool


def get_runtime(env: Mapping[str, str] | None = None) -> Runtime:
    values = os.environ if env is None else env
    role = values.get("APP_PROCESS_ROLE", "legacy").strip().lower()
    if role not in {"legacy", "api", "sync", "worker", "scheduler", "test"}:
        raise ValueError("Unsupported APP_PROCESS_ROLE")
    bootstrap = env_bool("DB_AUTO_BOOTSTRAP", role == "legacy", values)
    sync = env_bool("RUN_SYNC_WORKER", role in {"legacy", "sync"}, values)
    scheduler = env_bool("RUN_API_SCHEDULER", role == "legacy", values)
    if role != "legacy" and bootstrap:
        raise ValueError("DB_AUTO_BOOTSTRAP is allowed only in legacy mode; use a migration job")
    if role in {"api", "worker", "scheduler", "test"} and sync:
        raise ValueError("This process role cannot run the embedded sync worker")
    if role != "legacy" and scheduler:
        raise ValueError("Embedded API scheduler is allowed only in legacy mode")
    if env_bool("DURABLE_TASKS", False, values) and role in {"legacy", "sync"}:
        raise ValueError("Durable tasks require explicit api/worker/scheduler roles, never a legacy worker")
    if env_bool("REPORT_FRESHNESS_GUARDS", False, values) and (
            not env_bool("DURABLE_TASKS", False, values) or not env_bool("REPORT_DELIVERY_GUARDS", True, values)):
        raise ValueError("Report freshness requires durable tasks and delivery guards")
    if env_bool("DIRECT_EXPORT_FRESHNESS_GUARDS", False, values) and not env_bool("REPORT_FRESHNESS_GUARDS", False, values):
        raise ValueError("Direct export freshness requires report freshness")
    return Runtime(role, bootstrap, sync, scheduler)
