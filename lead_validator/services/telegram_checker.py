"""
Опциональная проверка регистрации номера в Telegram через Telethon.

Использует ImportContactsRequest: добавляем временный контакт по номеру,
если в ответе есть users — номер зарегистрирован в Telegram.
Требует авторизованную пользовательскую сессию (не бота).

Настройка:
1. Создайте приложение на https://my.telegram.org → API development tools
2. pip install telethon
3. Один раз выполните скрипт для входа и создания сессии (см. create_telegram_session.py)
4. В .env: TELEGRAM_CHECKER_API_ID, TELEGRAM_CHECKER_API_HASH, TELEGRAM_CHECKER_SESSION=путь/к/session

Ссылки:
- https://core.telegram.org/method/contacts.importContacts
- https://stackoverflow.com/questions/63967759/
"""

import logging
import os
import random
from typing import Optional

logger = logging.getLogger("lead_validator.telegram_checker")


async def check_phone_registered(phone: str) -> Optional[bool]:
    """
    Проверить, зарегистрирован ли номер в Telegram.
    
    Returns:
        True — номер зарегистрирован
        False — номер не зарегистрирован
        None — проверка недоступна
    """
    try:
        from telethon import TelegramClient
        from telethon.tl import functions, types
    except ImportError:
        logger.debug("Telethon not installed (pip install telethon), Telegram check disabled")
        return None

    from lead_validator.config import settings
    api_id = getattr(settings, "TELEGRAM_CHECKER_API_ID", "") or ""
    api_hash = getattr(settings, "TELEGRAM_CHECKER_API_HASH", "") or ""
    session_path = getattr(settings, "TELEGRAM_CHECKER_SESSION", "") or ""

    if not api_id or not api_hash or not session_path:
        return None

    session_path = session_path.strip()
    if not session_path.endswith(".session"):
        session_path = f"{session_path}.session"
    if not os.path.isfile(session_path):
        logger.debug(f"Telegram session file not found: {session_path}")
        return None

    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    if cleaned.startswith("8"):
        cleaned = "+7" + cleaned[1:]
    elif cleaned.startswith("7") and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if len(cleaned) < 10:
        return None

    try:
        client = TelegramClient(session_path, int(api_id), api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning("Telegram checker: session not authorized, re-run login script")
            await client.disconnect()
            return None

        client_id = random.randrange(-2**63, 2**63)
        result = await client(functions.contacts.ImportContactsRequest(
            contacts=[types.InputPhoneContact(client_id=client_id, phone=cleaned, first_name="Check", last_name="")]
        ))
        has_account = len(result.users) > 0
        if has_account:
            await client(functions.contacts.DeleteContactsRequest(result.users))
        await client.disconnect()
        return has_account
    except Exception as e:
        logger.debug(f"Telegram check failed for {phone}: {e}")
        return None
