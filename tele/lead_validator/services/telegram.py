"""
Telegram Bot для отправки уведомлений о новых лидах.
Улучшенная версия с подробным логированием для отладки.
"""

import logging
import httpx
from typing import Optional
from lead_validator.config import settings
from lead_validator.schemas import LeadInput

logger = logging.getLogger("lead_validator.telegram")


class TelegramNotifier:
    """
    Отправка уведомлений в Telegram при получении валидного лида.
    """
    
    BASE_URL = "https://api.telegram.org/bot"
    
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
            
        if lead.name:
            lines.append(f"👤 Имя: {lead.name}")
        if lead.email:
            lines.append(f"📧 Email: {lead.email}")
            
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
            
        message = self._format_lead_message(lead, phone_type, provider, region, is_test)
        
        logger.info(f"Sending Telegram notification for phone: {lead.phone} (is_test={is_test})")
        logger.debug(f"Message content: {message[:100]}...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
    
    async def send_message(self, text: str) -> bool:
        """
        Отправка произвольного сообщения (для отладки/уведомлений).
        """
        if not self.enabled:
            logger.warning("Telegram disabled, message not sent")
            return False
            
        if not self.token or not self.chat_id:
            logger.error("Telegram not configured properly")
            return False
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._get_url("sendMessage"),
                    json={
                        "chat_id": self.chat_id,
                        "text": text
                    }
                )
                
                if response.status_code == 200:
                    logger.info("Test message sent successfully")
                    return True
                else:
                    logger.error(f"Test message failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Test message error: {e}")
            
        return False
    
    async def test_connection(self) -> dict:
        """
        Тестирует соединение с Telegram API.
        Возвращает информацию о боте или ошибку.
        """
        if not self.token:
            return {"ok": False, "error": "Token not configured"}
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
