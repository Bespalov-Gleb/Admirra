"""Ночная автогенерация коротких AI-комментариев к дашборду (ТЗ §12).

Для каждого активного проекта с подключениями формируем комментарий по трём
стандартным периодам (эта неделя / этот месяц / последние 7 дней) и кэшируем
на клиенте. Не тратит AI-лимит тарифа — генерация серверная, фоновая.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm.attributes import flag_modified

from core.database import SessionLocal
from core import models
from ai.comment_periods import standard_periods

logger = logging.getLogger("ai.dashboard_comment_job")


async def generate_dashboard_comments() -> None:
    """Пересчитать и закэшировать AI-комментарии по стандартным периодам."""
    try:
        from ai.report_generator import generate_report as do_generate
    except ImportError as e:
        logger.warning("dashboard_comment autogen skipped — AI module unavailable: %s", e)
        return

    db = SessionLocal()
    try:
        clients = (
            db.query(models.Client)
            .filter(models.Client.status == models.ClientStatus.ACTIVE)
            .all()
        )
        periods = standard_periods()
        generated = 0
        for client in clients:
            has_integration = (
                db.query(models.Integration.id)
                .filter(models.Integration.client_id == client.id)
                .first()
            )
            if not has_integration:
                continue

            cache = dict(client.ai_comment_cache or {})
            changed = False
            for key, (start, end) in periods.items():
                try:
                    text = await do_generate(
                        db=db,
                        user_id=client.owner_id,
                        client_id=client.id,
                        start_date=start.isoformat(),
                        end_date=end.isoformat(),
                        report_type="dashboard_comment",
                    )
                except Exception as e:
                    logger.error("dashboard_comment autogen failed %s/%s: %s", client.id, key, e)
                    continue
                if text:
                    cache[key] = {
                        "text": text,
                        "generated_at": datetime.utcnow().isoformat(),
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    }
                    changed = True
                    generated += 1

            if changed:
                client.ai_comment_cache = cache
                flag_modified(client, "ai_comment_cache")
                latest = cache.get("last_7_days") or cache.get("this_week")
                if latest:
                    client.last_ai_comment = latest["text"]
                    client.last_ai_comment_at = datetime.utcnow()
                db.commit()
        logger.info("✅ dashboard_comment autogen: %d комментариев обновлено", generated)
    except Exception as e:
        logger.exception("dashboard_comment autogen crashed: %s", e)
        db.rollback()
    finally:
        db.close()
