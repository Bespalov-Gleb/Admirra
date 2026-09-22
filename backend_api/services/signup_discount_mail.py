"""Bounded reminder delivery; claim before SMTP, no blind retry on ambiguity."""
import asyncio
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from core import models
from core.database import SessionLocal
from backend_api.services.auth_mail import _send_sync
from backend_api.services import signup_discount as discount

log = logging.getLogger(__name__)


async def send_signup_discount_reminders(*, owner_id=None, limit=50):
    if not discount.any_enabled():
        return 0
    sent_count = 0
    for _ in range(1 if owner_id else min(limit, 50)):
        with SessionLocal.begin() as db:
            now = discount.now()
            q = db.query(models.User).filter(
                models.User.signup_discount_granted_at.is_not(None),
                models.User.signup_discount_used_at.is_(None),
                models.User.signup_discount_reminder_claimed_at.is_(None),
                models.User.signup_discount_expires_at > now + timedelta(days=1),
                models.User.signup_discount_expires_at <= now + timedelta(days=2),
            )
            if owner_id:
                q = q.filter(models.User.id == owner_id)
            if not discount.enabled():
                q = q.filter(models.User.id.in_(discount.pilot_user_ids()))
            user = q.order_by(models.User.signup_discount_expires_at).with_for_update(skip_locked=True).first()
            if not user:
                break
            # Claim even non-deliverable accounts to avoid scanning them forever.
            user.signup_discount_reminder_claimed_at = now
            sub = db.query(models.Subscription).filter(models.Subscription.user_id == user.id).order_by(models.Subscription.created_at.desc()).first()
            deliver = discount.active(db, user, sub) and user.email_verified and user.email and not user.email.endswith('@vk-oauth.admirra.ru')
            uid, email = user.id, user.email
            date = discount.aware(user.signup_discount_expires_at).astimezone(ZoneInfo('Europe/Moscow')).strftime('%d.%m')
        if not deliver:
            continue
        subject = f'Скидка 20% действует до {date}'
        body = (f'Пробный период заканчивается через два дня. До {date} на первую оплату любого '
                'доступного онлайн тарифа действует скидка 20% — потом она сгорает. '
                'Проекты и настройки после окончания пробного периода сохранятся.\n\n'
                'Выбрать тариф: https://admirra.ru/tariffs')
        try:
            html = (f'<p>Пробный период заканчивается через два дня. До {date} '
                    'на первую оплату доступного онлайн тарифа действует скидка 20%.</p>'
                    '<p>Проекты и настройки после окончания пробного периода сохранятся.</p>'
                    '<p><a href="https://admirra.ru/tariffs" style="display:inline-block;padding:12px 20px;'
                    'border-radius:8px;background:#2f6bea;color:#fff;text-decoration:none">Выбрать тариф</a></p>')
            sent = await asyncio.to_thread(_send_sync, email, subject, body, html_body=html)
        except Exception:
            sent = False
        if sent:
            with SessionLocal.begin() as db:
                db.query(models.User).filter(models.User.id == uid).update({models.User.signup_discount_reminder_sent_at: discount.now()})
            sent_count += 1
        else:
            log.warning('Signup discount reminder outcome unconfirmed; automatic resend disabled')
    return sent_count
