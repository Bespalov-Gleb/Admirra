import logging
from typing import Optional

import httpx
from fastapi import HTTPException

from core.config import get_config


logger = logging.getLogger(__name__)
cfg = get_config()

MAX_API_BASE = (cfg.oauth.max_api_base or "https://platform-api.max.ru").rstrip("/")
MAX_REPORTS_BOT_TOKEN = (cfg.oauth.max_reports_bot_token or "").strip()
MAX_REPORTS_BOT_NAME = (cfg.oauth.max_reports_bot_name or "").strip().lstrip("@")

_cached_bot_name: Optional[str] = None


def is_configured() -> bool:
    return bool(MAX_REPORTS_BOT_TOKEN)


async def resolve_bot_name() -> str:
    global _cached_bot_name
    if MAX_REPORTS_BOT_NAME:
        return MAX_REPORTS_BOT_NAME
    if _cached_bot_name:
        return _cached_bot_name
    if not MAX_REPORTS_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="MAX-бот для отчётов не настроен")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{MAX_API_BASE}/me",
            headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
        )
    try:
        data = response.json()
    except Exception:
        logger.warning("MAX reports /me returned non-JSON: %s %s", response.status_code, response.text[:300])
        raise HTTPException(status_code=503, detail="Не удалось получить имя MAX-бота для отчётов")

    if response.status_code != 200:
        logger.warning("MAX reports /me failed: %s %s", response.status_code, data)
        raise HTTPException(status_code=503, detail="MAX Bot API не вернул данные бота для отчётов")

    bot_name = str(data.get("username") or data.get("name") or "").strip().lstrip("@")
    if not bot_name:
        raise HTTPException(status_code=503, detail="У MAX-бота для отчётов не найден username")
    _cached_bot_name = bot_name
    return bot_name


async def send_message(
    text: str,
    *,
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
    format: Optional[str] = None,
) -> bool:
    if not MAX_REPORTS_BOT_TOKEN:
        logger.warning("MAX reports send skipped: MAX_REPORTS_BOT_TOKEN is empty")
        return False
    if not chat_id and not user_id:
        logger.warning("MAX reports send skipped: no chat_id or user_id")
        return False

    params = {}
    if chat_id:
        params["chat_id"] = chat_id
    else:
        params["user_id"] = user_id

    chunks = _split_text(text)
    ok = True
    async with httpx.AsyncClient(timeout=20.0) as client:
        for chunk in chunks:
            body = {"text": chunk}
            if format:
                body["format"] = format
            response = await client.post(
                f"{MAX_API_BASE}/messages",
                params=params,
                json=body,
                headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
            )
            if response.status_code >= 400:
                ok = False
                try:
                    data = response.json()
                except Exception:
                    data = response.text[:300]
                logger.warning("MAX reports message failed: %s %s", response.status_code, data)
    return ok


async def send_document(
    document: bytes,
    filename: str,
    *,
    caption: str = "",
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    """Отправляет файл (PDF-отчёт) в MAX: /uploads?type=file → multipart → token →
    /messages с attachment. При неудаче возвращает False (вызывающий может показать текст)."""
    if not MAX_REPORTS_BOT_TOKEN:
        logger.warning("MAX send_document skipped: token empty")
        return False
    if not chat_id and not user_id:
        logger.warning("MAX send_document skipped: no chat_id/user_id")
        return False

    params = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            up = await client.post(
                f"{MAX_API_BASE}/uploads",
                params={"type": "file"},
                headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
            )
            up_data = up.json() if up.status_code < 400 else {}
            upload_url = up_data.get("url")
            if not upload_url:
                logger.warning("MAX uploads failed: %s %s", up.status_code, up.text[:200])
                return False

            sent = await client.post(
                upload_url,
                files={"data": (filename, document, "application/pdf")},
            )
            sent_data = sent.json() if sent.status_code < 400 else {}
            token = sent_data.get("token") or (sent_data.get("file") or {}).get("token")
            if not token:
                logger.warning("MAX file upload failed: %s %s", sent.status_code, sent.text[:200])
                return False

            body = {
                "text": (caption or "")[:3900],
                "attachments": [{"type": "file", "payload": {"token": token}}],
            }
            resp = await client.post(
                f"{MAX_API_BASE}/messages",
                params=params,
                json=body,
                headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
            )
            if resp.status_code >= 400:
                logger.warning("MAX message with file failed: %s %s", resp.status_code, resp.text[:300])
                return False
            return True
    except Exception as e:
        logger.exception("MAX send_document error: %s", e)
        return False


def _split_text(text: str, limit: int = 3900) -> list[str]:
    value = (text or "").strip()
    if not value:
        return []
    chunks = []
    while len(value) > limit:
        cut = value.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(value[:cut].strip())
        value = value[cut:].strip()
    if value:
        chunks.append(value)
    return chunks
