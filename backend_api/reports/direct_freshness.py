"""Opt-in fail-closed direct exports: private short read transaction -> values.

No jobs, deliveries, provider calls, commits or caller Session rollback. The
renderer receives ordinary values after this session releases source locks.
Do not enable until durable writers exclusively maintain source coverage.
"""
from datetime import date, timedelta
from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy.orm import Session
from core import models
from core.data_requirements import DataNotReady
from core.runtime import env_bool
from backend_api.reports import freshness
from backend_api.stats_service import StatsService


def enabled():
    if not env_bool("DIRECT_EXPORT_FRESHNESS_GUARDS", False):
        return False
    if not freshness.enabled():
        raise RuntimeError("Direct export freshness requires report freshness")
    return True


def period(start, end, dynamics=False):
    try:
        start, end = date.fromisoformat(start), date.fromisoformat(end)
        if not 0 <= (end - start).days < 3660:
            raise ValueError()
        first = start - timedelta(days=(end - start).days + 1)
        if dynamics:
            year, month = divmod(end.year * 12 + end.month - 1 - 5, 12)
            first = min(first, date(year, month + 1, 1))
        return first, end
    except (TypeError, ValueError, OverflowError):
        raise DataNotReady("invalid_period") from None


def scope(db, user_id, client_id, folder_id):
    user = db.get(models.User, user_id)
    if not user or not user.is_active:
        raise DataNotReady("scope_unavailable")
    ids = (StatsService.resolve_folder_client_ids(db, user_id, folder_id)
           if folder_id and not client_id else StatsService.get_effective_client_ids(db, user_id, client_id))
    return sorted(set(ids), key=str)


@contextmanager
def _read_session(bind):
    try:
        with Session(bind=bind, autoflush=False) as read:
            # Local to this read: no production PostgreSQL settings changed.
            read.execute(sa.text("SET LOCAL lock_timeout = '1500ms'"))
            read.execute(sa.text("SET LOCAL statement_timeout = '20000ms'"))
            yield read
    except sa.exc.DBAPIError as exc:
        if getattr(exc.orig, "pgcode", None) in {"55P03", "57014"}:
            raise DataNotReady("source_busy") from None
        raise


def capture(db, user_id, client_id, folder_id, start, end, reader, *, dynamics=False, return_evidence=False):
    first, last = period(start, end, dynamics)
    bind = db.get_bind()
    # A Connection-bound Session may share a caller's transaction and locks.
    if not isinstance(bind, sa.engine.Engine):
        raise DataNotReady("isolated_read_unavailable")
    with _read_session(bind) as read:
        ids = scope(read, user_id, client_id, folder_id)
        from core.consumer_freshness import verify
        evidence = verify(read, ids, first, last)
        value = reader(read, ids)
        read.expire_all()
        if scope(read, user_id, client_id, folder_id) != ids:
            raise DataNotReady("scope_unavailable")
        return (value, evidence) if return_evidence else value


def preflight(db, user_id, client_id, folder_id, start, end, *, dynamics=False):
    """Cheap compared with a paid LLM; definitive check happens at capture too."""
    if enabled():
        capture(db, user_id, client_id, folder_id, start, end, lambda *_: None, dynamics=dynamics)
