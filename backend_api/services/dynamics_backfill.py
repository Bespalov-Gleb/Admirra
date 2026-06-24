"""
Бэкафилл истории для экрана «Динамика» (Phase 2 ТЗ).

Зачем: дашборд/Динамика читают из витрины фактов. У нового клиента (или после
короткого окна синка) глубокой истории в витрине нет — графики пустые. Этот
модуль по запросу догружает исторические данные из API площадок в витрину,
переиспользуя боевой фетчер `automation.sync.sync_integration`.

Дизайн (по ТЗ):
  • асинхронно, в фоне — пользователь не ждёт;
  • последовательно (НЕ конкурентно) — это обходит прежний дедлок параллельного
    force_full на общем рейт-лимитере; весь прогон идёт в ОДНОМ event-loop в
    выделенном потоке, поэтому APIRequestQueue (per-loop) не плодит cross-loop
    deadlock;
  • квота-aware — между чанками троттлинг; при сигнале лимита площадки (429 /
    units / quota) останавливаемся мягко и помечаем прогон частичным;
  • горизонт до 12 мес, чанки по 90 дней;
  • cooldown 1 час после прогона — нельзя дёргать бэкафилл слишком часто.

Статус хранится в памяти процесса. Backend поднят одним воркером uvicorn
(см. Dockerfile), поэтому single-process in-memory достаточно и не требует
миграций/новых таблиц.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import func

from core import models
from core.database import SessionLocal

logger = logging.getLogger(__name__)

BACKFILL_MONTHS = int(os.getenv("DYNAMICS_BACKFILL_MONTHS", "12"))
CHUNK_DAYS = int(os.getenv("DYNAMICS_BACKFILL_CHUNK_DAYS", "90"))
THROTTLE_SEC = float(os.getenv("DYNAMICS_BACKFILL_THROTTLE_SEC", "15"))
COOLDOWN_SEC = int(os.getenv("DYNAMICS_BACKFILL_COOLDOWN_SEC", "3600"))

_QUOTA_HINTS = ("429", "unit", "quota", "limit exceeded", "rate limit", "too many")

# key -> job dict. Защищено _state_lock.
_state_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def _key(client_ids: List) -> str:
    return "|".join(sorted(str(c) for c in client_ids)) or "none"


def _build_chunks(months: int, chunk_days: int):
    """Окна по chunk_days дней от (сегодня − months) до сегодня, от старых к новым."""
    today = date.today()
    start = today - timedelta(days=int(round(months * 30.5)))
    chunks = []
    cur = start
    while cur <= today:
        end = min(cur + timedelta(days=chunk_days - 1), today)
        chunks.append((cur, end))
        cur = end + timedelta(days=1)
    return chunks


def _earliest_data_date(db, client_ids: List) -> Optional[date]:
    dates = []
    for model in (models.YandexStats, models.VKStats, models.AvitoStats):
        d = (
            db.query(func.min(model.date))
            .filter(model.client_id.in_(client_ids))
            .scalar()
        )
        if d:
            dates.append(d)
    return min(dates) if dates else None


def _cooldown_until(job: Optional[dict]) -> Optional[datetime]:
    last_fin = (job or {}).get("last_finished_at")
    return (last_fin + timedelta(seconds=COOLDOWN_SEC)) if last_fin else None


def get_status(client_ids: List) -> dict:
    key = _key(client_ids)
    with _state_lock:
        job = dict(_jobs.get(key) or {})

    db = SessionLocal()
    try:
        hist_from = _earliest_data_date(db, client_ids)
    finally:
        db.close()

    cu = _cooldown_until(job)
    in_cooldown = bool(cu and datetime.utcnow() < cu)
    return {
        "status": job.get("status", "idle"),
        "running": job.get("status") == "running",
        "progress": int(job.get("progress", 0)),
        "steps_total": int(job.get("steps_total", 0)),
        "steps_done": int(job.get("steps_done", 0)),
        "message": job.get("message"),
        "error": job.get("error"),
        "in_cooldown": in_cooldown,
        "cooldown_until": (cu.isoformat() + "Z") if cu else None,
        "history_from": hist_from.isoformat() if hist_from else None,
        "months": BACKFILL_MONTHS,
    }


def start_backfill(client_ids: List, months: int = BACKFILL_MONTHS) -> dict:
    key = _key(client_ids)
    with _state_lock:
        job = _jobs.get(key)
        if job and job.get("status") == "running":
            return {"started": False, "reason": "already_running"}
        cu = _cooldown_until(job)
        if cu and datetime.utcnow() < cu:
            return {
                "started": False,
                "reason": "cooldown",
                "cooldown_until": cu.isoformat() + "Z",
            }

    db = SessionLocal()
    try:
        integration_ids = [
            r[0]
            for r in db.query(models.Integration.id)
            .filter(models.Integration.client_id.in_(client_ids))
            .all()
        ]
    finally:
        db.close()

    if not integration_ids:
        return {"started": False, "reason": "no_integrations"}

    chunks = _build_chunks(months, CHUNK_DAYS)
    steps_total = len(integration_ids) * len(chunks)

    with _state_lock:
        prev = _jobs.get(key) or {}
        _jobs[key] = {
            "status": "running",
            "progress": 0,
            "steps_total": steps_total,
            "steps_done": 0,
            "started_at": datetime.utcnow(),
            "finished_at": None,
            "last_finished_at": prev.get("last_finished_at"),
            "message": "Запуск загрузки истории…",
            "error": None,
        }

    t = threading.Thread(
        target=_thread_entry,
        args=(key, integration_ids, chunks),
        daemon=True,
        name=f"dyn-backfill-{key[:8]}",
    )
    t.start()
    logger.info(
        "Dynamics backfill started: key=%s integrations=%d chunks=%d steps=%d",
        key, len(integration_ids), len(chunks), steps_total,
    )
    return {"started": True, **get_status(client_ids)}


def _thread_entry(key: str, integration_ids: List, chunks: list):
    try:
        asyncio.run(_run_async(key, integration_ids, chunks))
    except Exception as e:  # noqa: BLE001
        logger.exception("Dynamics backfill crashed: %s", e)
        now = datetime.utcnow()
        with _state_lock:
            j = _jobs.get(key) or {}
            j.update(status="error", error=str(e)[:500], finished_at=now, last_finished_at=now)
            _jobs[key] = j


async def _run_async(key: str, integration_ids: List, chunks: list):
    # Ленивый импорт боевого фетчера — он тянет всю automation.sync.
    from automation.sync import sync_integration

    total = len(integration_ids) * len(chunks)
    done = 0
    stop = False

    for int_id in integration_ids:
        if stop:
            break
        for d_from, d_to in chunks:
            df_s, dt_s = d_from.isoformat(), d_to.isoformat()
            db = SessionLocal()
            try:
                integ = (
                    db.query(models.Integration)
                    .filter(models.Integration.id == int_id)
                    .first()
                )
                if not integ:
                    break
                with _state_lock:
                    if key in _jobs:
                        _jobs[key]["message"] = f"{integ.platform}: {df_s} … {dt_s}"
                await sync_integration(db, integ, df_s, dt_s)
                db.commit()
            except Exception as e:  # noqa: BLE001
                db.rollback()
                msg = str(e).lower()
                if any(h in msg for h in _QUOTA_HINTS):
                    logger.warning("Backfill stopped on quota signal: %s", e)
                    with _state_lock:
                        if key in _jobs:
                            _jobs[key]["message"] = (
                                "Достигнут лимит API площадки — остальная история догрузится позже"
                            )
                    stop = True
                else:
                    logger.warning(
                        "Backfill chunk failed (int=%s %s-%s): %s", int_id, df_s, dt_s, e
                    )
            finally:
                db.close()

            if stop:
                break

            done += 1
            with _state_lock:
                if key in _jobs:
                    _jobs[key]["steps_done"] = done
                    _jobs[key]["progress"] = int(done / total * 100) if total else 100
            await asyncio.sleep(THROTTLE_SEC)

    now = datetime.utcnow()
    with _state_lock:
        j = _jobs.get(key) or {}
        j["status"] = "partial" if stop else "done"
        if not stop:
            j["progress"] = 100
            j["message"] = "История загружена"
        j["finished_at"] = now
        j["last_finished_at"] = now
        _jobs[key] = j
    logger.info("Dynamics backfill finished: key=%s status=%s steps=%d/%d",
                key, "partial" if stop else "done", done, total)
