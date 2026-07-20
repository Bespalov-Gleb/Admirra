import asyncio
import logging
from contextvars import ContextVar
from typing import Optional

import httpx
from fastapi import HTTPException

from core.config import get_config


logger = logging.getLogger(__name__)
cfg = get_config()

# MAX завершил миграцию API 19.07.2026. Конфигурация автоматически заменяет
# старый домен на актуальный endpoint, сохраняя поддержку кастомного proxy.
MAX_API_BASE = (cfg.oauth.max_api_base or "https://platform-api2.max.ru").rstrip("/")
MAX_REPORTS_BOT_TOKEN = (cfg.oauth.max_reports_bot_token or "").strip()
MAX_REPORTS_BOT_NAME = (cfg.oauth.max_reports_bot_name or "").strip().lstrip("@")

_cached_bot_name: Optional[str] = None
_last_delivery_error: ContextVar[Optional[str]] = ContextVar("max_reports_delivery_error", default=None)


def _set_delivery_error(value: Optional[str]) -> None:
    _last_delivery_error.set(value)


def get_last_delivery_error() -> Optional[str]:
    """Причина последней попытки в текущей async-задаче, без токенов и PII."""
    return _last_delivery_error.get()


def _response_error(prefix: str, response: httpx.Response) -> str:
    """Берём только безопасные поля, которые MAX возвращает для диагностики."""
    detail = ""
    try:
        data = response.json()
        if isinstance(data, dict):
            code = str(data.get("code") or data.get("error") or "").strip()
            message = str(data.get("message") or data.get("description") or "").strip()
            detail = ": ".join(value for value in (code, message) if value)
    except Exception:
        detail = ""
    if not detail:
        detail = f"HTTP {response.status_code}"
    return f"MAX: {prefix} — {detail[:300]}"


def _request_error(prefix: str, exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        detail = "тайм-аут API"
    elif isinstance(exc, httpx.ConnectError):
        detail = "не удалось подключиться к API"
    elif isinstance(exc, httpx.RequestError):
        detail = "ошибка сетевого запроса"
    else:
        detail = type(exc).__name__
    return f"MAX: {prefix} — {detail}"


def _is_attachment_not_ready(response: httpx.Response) -> bool:
    try:
        data = response.json()
    except Exception:
        return False
    return isinstance(data, dict) and str(data.get("code") or "").strip().lower() == "attachment.not.ready"


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

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{MAX_API_BASE}/me",
                headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
            )
    except httpx.RequestError as exc:
        logger.warning("MAX reports /me failed: %s", _request_error("проверка бота", exc))
        raise HTTPException(status_code=503, detail="MAX Bot API недоступен") from exc
    try:
        data = response.json()
    except Exception:
        logger.warning("MAX reports /me returned non-JSON: %s", response.status_code)
        raise HTTPException(status_code=503, detail="Не удалось получить имя MAX-бота для отчётов")

    if response.status_code != 200:
        logger.warning("MAX reports /me failed: %s", _response_error("проверка бота", response))
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
    _set_delivery_error(None)
    if not MAX_REPORTS_BOT_TOKEN:
        _set_delivery_error("MAX: токен бота для отчётов не настроен")
        logger.warning("MAX reports send skipped: MAX_REPORTS_BOT_TOKEN is empty")
        return False
    if not chat_id and not user_id:
        _set_delivery_error("MAX: получатель не привязан")
        logger.warning("MAX reports send skipped: no chat_id or user_id")
        return False

    params = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
    chunks = _split_text(text)
    if not chunks:
        _set_delivery_error("MAX: пустой текст сообщения")
        return False
    try:
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
                    error = _response_error("отправка сообщения", response)
                    _set_delivery_error(error)
                    logger.warning("MAX reports message failed: %s", error)
                    return False
    except Exception as exc:
        error = _request_error("отправка сообщения", exc)
        _set_delivery_error(error)
        logger.warning("MAX reports message failed: %s", error)
        return False
    return True


async def send_document(
    document: bytes,
    filename: str,
    *,
    caption: str = "",
    content_type: str = "application/pdf",
    chat_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    """Отправляет отчёт через /uploads → token → /messages.

    MAX обрабатывает вложение асинхронно и может кратковременно вернуть
    ``attachment.not.ready``. Это штатный случай: повторяем только финальный
    запрос после короткой задержки, не загружая и не дублируя файл заново.
    """
    _set_delivery_error(None)
    if not MAX_REPORTS_BOT_TOKEN:
        _set_delivery_error("MAX: токен бота для отчётов не настроен")
        logger.warning("MAX send_document skipped: token empty")
        return False
    if not document:
        _set_delivery_error("MAX: файл отчёта пуст")
        return False
    if not chat_id and not user_id:
        _set_delivery_error("MAX: получатель не привязан")
        logger.warning("MAX send_document skipped: no chat_id/user_id")
        return False

    params = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
    attachment_type = "image" if (content_type or "").lower().startswith("image/") else "file"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upload_meta = await client.post(
                f"{MAX_API_BASE}/uploads",
                params={"type": attachment_type},
                headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
            )
            if upload_meta.status_code >= 400:
                error = _response_error("подготовка загрузки", upload_meta)
                _set_delivery_error(error)
                logger.warning("MAX uploads failed: %s", error)
                return False
            try:
                upload_url = (upload_meta.json() or {}).get("url")
            except Exception:
                upload_url = None
            if not upload_url:
                error = "MAX: подготовка загрузки — API не вернул URL"
                _set_delivery_error(error)
                logger.warning(error)
                return False

            uploaded = await client.post(
                upload_url,
                files={"data": (filename, document, content_type)},
            )
            if uploaded.status_code >= 400:
                error = _response_error("загрузка файла", uploaded)
                _set_delivery_error(error)
                logger.warning("MAX file upload failed: %s", error)
                return False
            try:
                uploaded_data = uploaded.json() or {}
            except Exception:
                uploaded_data = {}
            token = uploaded_data.get("token") or (uploaded_data.get("file") or {}).get("token")
            if not token:
                error = "MAX: загрузка файла — API не вернул токен вложения"
                _set_delivery_error(error)
                logger.warning(error)
                return False

            body = {
                "text": (caption or "")[:3900],
                "attachments": [{"type": attachment_type, "payload": {"token": token}}],
            }
            for attempt, delay in enumerate((0, 1, 2, 4)):
                if delay:
                    await asyncio.sleep(delay)
                response = await client.post(
                    f"{MAX_API_BASE}/messages",
                    params=params,
                    json=body,
                    headers={"Authorization": MAX_REPORTS_BOT_TOKEN},
                )
                if response.status_code < 400:
                    return True
                if _is_attachment_not_ready(response) and attempt < 3:
                    logger.info("MAX attachment is not ready yet; retrying final send in %ss", (1, 2, 4)[attempt])
                    continue
                error = _response_error("отправка вложения", response)
                _set_delivery_error(error)
                logger.warning("MAX message with file failed: %s", error)
                return False
    except Exception as exc:
        error = _request_error("отправка вложения", exc)
        _set_delivery_error(error)
        logger.warning("MAX send_document failed: %s", error)
        return False
    _set_delivery_error("MAX: вложение не было подтверждено API")
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
