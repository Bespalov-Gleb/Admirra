import asyncio
import logging
from typing import Optional

from core.config import get_config
from core.public_domain import resolve_frontend_url
from .auth_mail import _send_sync, smtp_delivery_active

logger = logging.getLogger("api.team_mail")

FRONTEND_URL = resolve_frontend_url().rstrip("/")


def _button_html(label: str, url: str) -> str:
    return (
        f'<p style="margin:24px 0;">'
        f'<a href="{url}" style="display:inline-block;padding:12px 24px;background:#2563eb;'
        f'color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;">{label}</a>'
        f"</p>"
    )


def _html_wrapper(title: str, body_html: str) -> str:
    return (
        f'<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#171717;'
        f'line-height:1.5;max-width:560px;margin:0 auto;padding:24px;">'
        f"<h2 style=\"margin:0 0 16px;\">{title}</h2>{body_html}"
        f'<p style="color:#696969;font-size:13px;margin-top:32px;">Команда AdMirra</p>'
        f"</body></html>"
    )


def _invite_urls(token: str) -> tuple[str, str]:
    accept_url = f"{FRONTEND_URL}/team/accept?token={token}"
    register_url = f"{FRONTEND_URL}/register?invite={token}"
    return accept_url, register_url


async def send_team_member_invite_email(
    to_email: str,
    inviter_email: str,
    invite_token: str,
) -> bool:
    if not smtp_delivery_active():
        return False
    accept_url, register_url = _invite_urls(invite_token)
    subject = "Вас добавили в команду AdMirra"
    plain = (
        f"Здравствуйте!\n\n"
        f"{inviter_email} пригласил(а) вас в команду AdMirra как сотрудника.\n\n"
        f"Принять приглашение: {accept_url}\n"
        f"Если у вас ещё нет аккаунта — зарегистрируйтесь: {register_url}\n"
    )
    html = _html_wrapper(
        subject,
        f"<p>Здравствуйте!</p>"
        f"<p><strong>{inviter_email}</strong> пригласил(а) вас в команду AdMirra как сотрудника.</p>"
        f"{_button_html('Принять приглашение', accept_url)}"
        f"<p style=\"color:#696969;font-size:14px;\">Нет аккаунта? "
        f'<a href="{register_url}">Зарегистрироваться</a></p>',
    )
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, plain, None, html)
    except Exception as e:
        logger.exception("send_team_member_invite_email failed: %s", e)
        return False


async def send_team_client_invite_email(
    to_email: str,
    inviter_email: str,
    invite_token: str,
) -> bool:
    if not smtp_delivery_active():
        return False
    accept_url, register_url = _invite_urls(invite_token)
    subject = "Вам открыли доступ к аналитике AdMirra"
    plain = (
        f"Здравствуйте!\n\n"
        f"{inviter_email} пригласил(а) вас как клиента в AdMirra.\n\n"
        f"Посмотреть: {accept_url}\n"
        f"Регистрация: {register_url}\n"
    )
    html = _html_wrapper(
        subject,
        f"<p>Здравствуйте!</p>"
        f"<p><strong>{inviter_email}</strong> открыл(а) вам доступ к аналитике AdMirra.</p>"
        f"{_button_html('Посмотреть', accept_url)}"
        f"<p style=\"color:#696969;font-size:14px;\">Нет аккаунта? "
        f'<a href="{register_url}">Зарегистрироваться</a></p>',
    )
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, plain, None, html)
    except Exception as e:
        logger.exception("send_team_client_invite_email failed: %s", e)
        return False


async def send_team_client_project_access_email(
    to_email: str,
    inviter_email: str,
    project_name: str,
    view_url: Optional[str] = None,
) -> bool:
    if not smtp_delivery_active():
        return False
    url = view_url or f"{FRONTEND_URL}/"
    subject = f"Вам открыли доступ к аналитике проекта {project_name}"
    plain = (
        f"Здравствуйте!\n\n"
        f"{inviter_email} открыл(а) вам доступ к проекту «{project_name}».\n\n"
        f"Посмотреть: {url}\n"
    )
    html = _html_wrapper(
        "Доступ к проекту",
        f"<p>Здравствуйте!</p>"
        f"<p><strong>{inviter_email}</strong> открыл(а) вам доступ к аналитике проекта "
        f"<strong>«{project_name}»</strong>.</p>"
        f"{_button_html('Посмотреть', url)}",
    )
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, plain, None, html)
    except Exception as e:
        logger.exception("send_team_client_project_access_email failed: %s", e)
        return False


# Обратная совместимость
async def send_team_invite_email(to_email: str, inviter_email: str, role_label: str) -> bool:
    logger.warning("send_team_invite_email deprecated; use role-specific templates")
    return False
