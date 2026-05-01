import asyncio
import logging

from .auth_mail import _send_sync, smtp_delivery_active

logger = logging.getLogger("api.team_mail")


async def send_team_invite_email(to_email: str, inviter_email: str, role_label: str) -> bool:
    if not smtp_delivery_active():
        return False
    subject = "Приглашение в команду AdMirra"
    body = (
        f"Здравствуйте!\n\n"
        f"Вас пригласили в AdMirra как {role_label}.\n"
        f"Приглашение отправил: {inviter_email}\n\n"
        f"Если у вас уже есть аккаунт с этим email — просто войдите в систему.\n"
        f"Если аккаунта нет — зарегистрируйтесь на этот email, и доступ активируется.\n"
    )
    try:
        return await asyncio.to_thread(_send_sync, to_email, subject, body)
    except Exception as e:
        logger.exception("send_team_invite_email failed: %s", e)
        return False
