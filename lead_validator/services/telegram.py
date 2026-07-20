"""
Telegram Bot для отправки уведомлений о новых лидах.
Улучшенная версия с подробным логированием для отладки.
"""

import logging
from contextvars import ContextVar
from datetime import datetime
import httpx
from typing import Optional, Any
from lead_validator.config import settings
from lead_validator.schemas import LeadInput

logger = logging.getLogger("lead_validator.telegram")
_last_delivery_error: ContextVar[Optional[str]] = ContextVar("telegram_delivery_error", default=None)


def _set_delivery_error(value: Optional[str]) -> None:
    _last_delivery_error.set(value)


def get_last_delivery_error() -> Optional[str]:
    """Причина последней доставки в текущей async-задаче без chat_id и токена."""
    return _last_delivery_error.get()


def _telegram_response_error(method: str, response: httpx.Response) -> str:
    detail = ""
    try:
        data = response.json()
        if isinstance(data, dict):
            detail = str(data.get("description") or data.get("error_code") or "").strip()
    except Exception:
        detail = ""
    if not detail:
        detail = f"HTTP {response.status_code}"
    return f"Telegram: {method} — {detail[:300]}"


def _telegram_request_error(method: str, exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        detail = "тайм-аут API"
    elif isinstance(exc, httpx.ConnectError):
        detail = "не удалось подключиться к API"
    elif isinstance(exc, httpx.RequestError):
        detail = "ошибка сетевого запроса"
    else:
        detail = type(exc).__name__
    return f"Telegram: {method} — {detail}"


class TelegramNotifier:
    """
    Отправка уведомлений в Telegram при получении валидного лида.
    """
    
    import os as _os
    # TELEGRAM_API_BASE — обход блокировки api.telegram.org с РФ-хостинга (свой прокси)
    BASE_URL = (_os.getenv("TELEGRAM_API_BASE") or "https://api.telegram.org").rstrip("/") + "/bot"
    
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = settings.TELEGRAM_ENABLED
        
        # Логируем состояние при инициализации
        if self.enabled:
            logger.info(f"Telegram notifications ENABLED")
            logger.info(f"Chat ID: {self.chat_id}")
            logger.info(f"Token configured: {'YES' if self.token else 'NO'}")
        else:
            logger.warning("Telegram notifications DISABLED")
        
    def _get_url(self, method: str) -> str:
        """Формирует URL для вызова Telegram API"""
        return f"{self.BASE_URL}{self.token}/{method}"
    
    def _format_lead_message(
        self, 
        lead: LeadInput, 
        phone_type: Optional[str] = None,
        provider: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        social_result: Optional[Any] = None,
        project_name: Optional[str] = None,
        source: Optional[str] = None,
        is_test: bool = False
    ) -> str:
        """
        Форматирует сообщение о новом лиде.
        
        Использует Markdown для красивого отображения.
        """
        title = "🧪 *ТЕСТОВАЯ ЗАЯВКА*" if is_test else "🆕 *Новая заявка!*"
        
        lines = [
            title,
            "",
            f"📞 Телефон: `{lead.phone}`"
        ]
        
        if phone_type:
            lines.append(f"📱 Тип: {phone_type}")
        if provider:
            lines.append(f"📡 Оператор: {provider}")
        if region:
            lines.append(f"📍 Регион: {region}")
        if city:
            lines.append(f"🏙 Город: {city}")
            
        if lead.name:
            lines.append(f"👤 Имя: {lead.name}")
        if lead.email:
            lines.append(f"📧 Email: {lead.email}")
        
        # Соцсети и мессенджеры
        if social_result and getattr(social_result, "checked", False):
            social_parts = []
            if getattr(social_result, "has_telegram", None):
                un = getattr(social_result, "telegram_username", None)
                social_parts.append(f"TG{' (@' + un + ')' if un else ''}")
            if getattr(social_result, "has_whatsapp", None):
                social_parts.append("WA")
            if getattr(social_result, "has_viber", None):
                social_parts.append("Viber")
            if getattr(social_result, "has_vk", None):
                social_parts.append("VK")
            if getattr(social_result, "has_tiktok", None):
                social_parts.append("TikTok")
            if social_parts:
                lines.append(f"💬 Мессенджеры: {', '.join(social_parts)}")
            
        # Проект и источник
        if project_name:
            lines.append(f"📋 Проект: {project_name}")
        if source:
            lines.append(f"📥 Источник: {source}")
            
        # Время
        lines.append(f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            
        # UTM метки
        utm_parts = []
        if lead.utm_source:
            utm_parts.append(f"source={lead.utm_source}")
        if lead.utm_medium:
            utm_parts.append(f"medium={lead.utm_medium}")
        if lead.utm_campaign:
            utm_parts.append(f"campaign={lead.utm_campaign}")
            
        if utm_parts:
            lines.append("")
            lines.append(f"🔗 UTM: {', '.join(utm_parts)}")
            
        return "\n".join(lines)
    
    async def send_new_lead(
        self, 
        lead: LeadInput,
        phone_type: Optional[str] = None,
        provider: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        social_result: Optional[Any] = None,
        project_name: Optional[str] = None,
        source: Optional[str] = None,
        is_test: bool = False
    ) -> bool:
        """
        Отправляет уведомление о новом лиде.
        """
        if not self.enabled and not is_test:  # Тестовые отправляем даже если выключено (если явно вызвано)
             # Но если токена нет, то не отправим все равно. 
             # Логика: если self.enabled=False, мы вообще не должны слать продакшн лиды.
             # А тестовые? Пользователь может хотеть проверить отправку даже если основной поток выключен?
             # Пока оставим строгую проверку enabled, чтобы не спамить если выключено.
             pass
             
        if not self.enabled:
            logger.warning(f"Telegram DISABLED - skipping notification for: {lead.phone}")
            return False
            
        if not self.token:
            logger.error("Telegram token not configured!")
            return False
            
        if not self.chat_id:
            logger.error("Telegram chat_id not configured!")
            return False
            
        message = self._format_lead_message(
            lead, phone_type, provider, region, city,
            social_result, project_name, source, is_test
        )
        
        logger.info(f"Sending Telegram notification for phone: {lead.phone} (is_test={is_test})")
        logger.debug(f"Message content: {message[:100]}...")
        
        try:
            async with httpx.AsyncClient(verify=(__import__("os").getenv("TELEGRAM_API_VERIFY") or "true").strip().lower() not in ("false","0","no"), timeout=10.0) as client:
                url = self._get_url("sendMessage")
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                
                logger.debug(f"Request URL: {url}")
                logger.debug(f"Request payload: chat_id={self.chat_id}, text_length={len(message)}")
                
                response = await client.post(url, json=payload)
                
                logger.info(f"Telegram API response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"✅ Telegram notification SENT for phone: {lead.phone}")
                        return True
                    else:
                        logger.error(f"Telegram API error: {result}")
                        return False
                else:
                    response_text = response.text
                    logger.error(
                        f"❌ Telegram API HTTP error: {response.status_code}\n"
                        f"Response: {response_text}"
                    )
                    
                    # Попробуем распарсить JSON для более детальной ошибки
                    try:
                        error_data = response.json()
                        error_code = error_data.get("error_code")
                        description = error_data.get("description")
                        logger.error(f"Telegram error details: [{error_code}] {description}")
                    except:
                        pass
                    
        except httpx.TimeoutException:
            logger.warning(f"⏳ Telegram request TIMEOUT for phone: {lead.phone}")
        except httpx.ConnectError as e:
            logger.error(f"🔌 Telegram connection error: {e}")
        except Exception as e:
            logger.error(f"💥 Telegram unexpected error: {type(e).__name__}: {e}")
            
        return False
    
    async def send_document(
        self,
        chat_id: str,
        document: bytes,
        filename: str = "report.pdf",
        caption: Optional[str] = None,
    ) -> bool:
        """
        Отправка документа (PDF) в Telegram.
        chat_id — ID чата (может отличаться от дефолтного self.chat_id).
        """
        _set_delivery_error(None)
        if not self.token:
            _set_delivery_error("Telegram: токен бота для отчётов не настроен")
            logger.error("Telegram token not configured")
            return False
        if not chat_id:
            _set_delivery_error("Telegram: получатель не привязан")
            logger.error("chat_id required for send_document")
            return False
        try:
            async with httpx.AsyncClient(verify=(__import__("os").getenv("TELEGRAM_API_VERIFY") or "true").strip().lower() not in ("false","0","no"), timeout=60.0) as client:
                url = self._get_url("sendDocument")
                files = {"document": (filename, document, "application/pdf")}
                data = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption
                response = await client.post(url, data=data, files=files)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"Document sent to {chat_id}")
                        return True
                error = _telegram_response_error("отправка PDF", response)
                _set_delivery_error(error)
                logger.warning("sendDocument failed: %s", error)
        except Exception as exc:
            error = _telegram_request_error("отправка PDF", exc)
            _set_delivery_error(error)
            logger.warning("send_document failed: %s", error)
        return False

    async def send_photo(
        self,
        chat_id: str,
        photo: bytes,
        caption: Optional[str] = None,
    ) -> bool:
        """Отправляет PNG-превью отчёта с текстом и ссылкой на PDF."""
        _set_delivery_error(None)
        if not self.token:
            _set_delivery_error("Telegram: токен бота для отчётов не настроен")
            logger.error("Telegram token not configured")
            return False
        if not chat_id:
            _set_delivery_error("Telegram: получатель не привязан")
            logger.error("chat_id required for send_photo")
            return False
        try:
            verify = (__import__("os").getenv("TELEGRAM_API_VERIFY") or "true").strip().lower() not in ("false", "0", "no")
            async with httpx.AsyncClient(verify=verify, timeout=60.0) as client:
                response = await client.post(
                    self._get_url("sendPhoto"),
                    data={"chat_id": chat_id, **({"caption": caption[:1024]} if caption else {})},
                    files={"photo": ("report.png", photo, "image/png")},
                )
                if response.status_code == 200 and (response.json() or {}).get("ok"):
                    return True
                error = _telegram_response_error("отправка PNG", response)
                _set_delivery_error(error)
                logger.warning("sendPhoto failed: %s", error)
        except Exception as exc:
            error = _telegram_request_error("отправка PNG", exc)
            _set_delivery_error(error)
            logger.warning("send_photo failed: %s", error)
        return False

    async def send_message(self, text: str, parse_mode: str = "Markdown", chat_id: Optional[str] = None) -> bool:
        """
        Отправка произвольного сообщения (для отладки/уведомлений/алертов).
        
        Args:
            text: Текст сообщения
            parse_mode: Режим форматирования (Markdown, HTML, или None)
            chat_id: ID чата (если не указан — используется self.chat_id)
        """
        if not self.enabled:
            logger.warning("Telegram disabled, message not sent")
            return False

        target_chat = chat_id or self.chat_id
        if not self.token or not target_chat:
            logger.error("Telegram not configured properly")
            return False

        try:
            async with httpx.AsyncClient(verify=(__import__("os").getenv("TELEGRAM_API_VERIFY") or "true").strip().lower() not in ("false","0","no"), timeout=10.0) as client:
                payload = {
                    "chat_id": target_chat,
                    "text": text
                }
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                
                response = await client.post(
                    self._get_url("sendMessage"),
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info("Message sent successfully")
                        return True
                    else:
                        logger.error(f"Telegram API error: {result}")
                else:
                    logger.error(f"Message failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Message error: {e}")
            
        return False
    
    async def test_connection(self) -> dict:
        """
        Тестирует соединение с Telegram API.
        Возвращает информацию о боте или ошибку.
        """
        if not self.token:
            return {"ok": False, "error": "Token not configured"}
            
        try:
            async with httpx.AsyncClient(verify=(__import__("os").getenv("TELEGRAM_API_VERIFY") or "true").strip().lower() not in ("false","0","no"), timeout=10.0) as client:
                # Проверяем бота
                me_response = await client.get(self._get_url("getMe"))
                me_data = me_response.json()
                
                if not me_data.get("ok"):
                    return {"ok": False, "error": f"Invalid token: {me_data}"}
                    
                bot_info = me_data.get("result", {})
                
                # Пробуем отправить тестовое сообщение
                test_msg = "🔧 Lead Validator: Тестовое подключение успешно!"
                send_response = await client.post(
                    self._get_url("sendMessage"),
                    json={"chat_id": self.chat_id, "text": test_msg}
                )
                send_data = send_response.json()
                
                return {
                    "ok": send_data.get("ok", False),
                    "bot_username": bot_info.get("username"),
                    "bot_name": bot_info.get("first_name"),
                    "chat_id": self.chat_id,
                    "test_message_sent": send_data.get("ok", False),
                    "error": send_data.get("description") if not send_data.get("ok") else None
                }
                
        except Exception as e:
            return {"ok": False, "error": str(e)}


# Глобальный экземпляр
telegram_notifier = TelegramNotifier()
