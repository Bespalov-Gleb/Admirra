"""§9.2: ночной прогрев AI-комментариев для «тёплых» проектов.

Тёплый проект — дашборд открывали за последние warm_window_days. Для таких
проектов после ночного синка заранее генерируем комментарий дефолтного пресета
(«эта неделя»), чтобы он был готов к приходу человека. Экономика §9:
- лимит AI-запросов не тратится (dashboard_comment не списывает квоту);
- троттлинг: не чаще раза в ~сутки на проект и только если данные изменились;
- при достижении comments_soft_cap на аккаунт ночной прогрев пропускаем (§9.4).
"""

import logging
from datetime import datetime, timedelta, timezone

from core import models, pricing
from core.config import get_config
from core.database import SessionLocal

logger = logging.getLogger("ai.prewarm")

_THROTTLE = timedelta(hours=20)


def _aware(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


async def prewarm_warm_project_comments() -> None:
    from ai.report_generator import generate_report
    from ai.router import _comment_fingerprint, _save_comment_cache
    from ai.comment_periods import standard_periods
    from backend_api.services.subscription import SubscriptionService

    db = SessionLocal()
    try:
        cfg = get_config()
        warm_days = int(getattr(cfg.billing, "warm_window_days", 7) or 7)
        now = datetime.now(timezone.utc)
        warm_since = now - timedelta(days=warm_days)

        clients = (
            db.query(models.Client)
            .filter(
                models.Client.status == models.ClientStatus.ACTIVE,
                models.Client.last_dashboard_viewed_at.isnot(None),
                models.Client.last_dashboard_viewed_at >= warm_since,
            )
            .all()
        )
        if not clients:
            logger.info("Прогрев комментариев: тёплых проектов нет")
            return

        d_start, d_end = standard_periods()["this_week"]
        start_s, end_s = d_start.isoformat(), d_end.isoformat()
        soft_cap_cache: dict = {}
        generated = 0

        for client in clients:
            try:
                lcg = _aware(getattr(client, "last_comment_generated_at", None))
                owner_id = client.owner_id
                # §9.4: soft_cap на аккаунт. При превышении не блокируем совсем, а
                # снижаем частоту ночного прогрева до раза в трое суток.
                if owner_id not in soft_cap_cache:
                    owner = db.query(models.User).filter(models.User.id == owner_id).first()
                    cap = 0
                    used = 0
                    if owner is not None:
                        plan = SubscriptionService.get_user_plan(db, owner)
                        cap = pricing.resolve_plan(plan.code).effective_comments_soft_cap
                        since = now - timedelta(days=30)
                        used = (
                            db.query(models.AICommentGeneration)
                            .join(models.Client, models.Client.id == models.AICommentGeneration.client_id)
                            .filter(models.Client.owner_id == owner_id,
                                    models.AICommentGeneration.generated_at >= since)
                            .count()
                        )
                    soft_cap_cache[owner_id] = (cap, used)
                cap, used = soft_cap_cache[owner_id]
                over_cap = bool(cap) and used >= cap
                throttle = timedelta(hours=72) if over_cap else _THROTTLE
                if lcg and (now - lcg) < throttle:
                    continue

                # §9.2: только если данные изменились с прошлой генерации.
                fp = _comment_fingerprint(db, owner_id, client.id, start_s, end_s)
                cache = getattr(client, "ai_comment_cache", None) or {}
                from ai.comment_periods import period_key_for
                pk = period_key_for(start_s, end_s)
                entry = cache.get(pk) if isinstance(cache, dict) and pk else None
                if entry and fp and entry.get("fingerprint") == fp:
                    continue

                text = await generate_report(
                    db=db, user_id=owner_id, client_id=client.id,
                    start_date=start_s, end_date=end_s,
                    report_type="dashboard_comment", trigger="auto_sync",
                )
                if text:
                    _save_comment_cache(db, client.id, start_s, end_s, text, fingerprint=fp)
                    client.last_comment_generated_at = now
                    db.commit()
                    soft_cap_cache[owner_id] = (cap, used + 1)
                    generated += 1
            except Exception as e:
                db.rollback()
                logger.warning("Прогрев комментария не удался для проекта %s: %s", client.id, e)

        logger.info("Прогрев комментариев: сгенерировано %d из %d тёплых проектов", generated, len(clients))
    finally:
        db.close()
