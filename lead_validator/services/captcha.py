"""
Сервис валидации Yandex SmartCaptcha.
Проверяет токен капчи через Yandex API.
"""

import logging
import httpx
from typing import Tuple, Optional
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.captcha")

YANDEX_VALIDATE_URL = "https://smartcaptcha.yandexcloud.net/validate"


async def validate_smartcaptcha(token: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Проверяет токен Yandex SmartCaptcha.
    
    Args:
        token: Токен капчи (smart-token) от клиента
        client_ip: IP адрес клиента (опционально, рекомендуется)
    
    Returns:
        Tuple[bool, str]: (успех, сообщение об ошибке если есть)
    """
    if not settings.SMARTCAPTCHA_ENABLED:
        logger.debug("SmartCaptcha disabled, skipping validation")
        return True, ""
    
    if not settings.SMARTCAPTCHA_SERVER_KEY:
        logger.warning("SmartCaptcha enabled but server key not set!")
        # Fail-open: пропускаем если ключ не настроен
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: server configuration error"
    
    if not token:
        logger.info("SmartCaptcha token missing")
        return False, "CAPTCHA: token required"
    
    try:
        params = {
            "secret": settings.SMARTCAPTCHA_SERVER_KEY,
            "token": token,
        }
        if client_ip:
            params["ip"] = client_ip
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(YANDEX_VALIDATE_URL, params=params)
            data = response.json()
        
        logger.debug(f"SmartCaptcha response: {data}")
        
        if data.get("status") == "ok":
            logger.info("SmartCaptcha validation passed")
            return True, ""
        else:
            message = data.get("message", "validation failed")
            logger.warning(f"SmartCaptcha validation failed: {message}")
            return False, f"CAPTCHA: {message}"
            
    except httpx.TimeoutException:
        logger.error("SmartCaptcha API timeout")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: service timeout"
        
    except Exception as e:
        logger.error(f"SmartCaptcha error: {e}")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, f"CAPTCHA: service error"


# Экземпляр-синглтон для импорта
class CaptchaValidator:
    """Singleton класс для валидации капчи."""
    
    async def validate(self, token: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
        """Валидация токена капчи."""
        return await validate_smartcaptcha(token, client_ip)
    
    def is_enabled(self) -> bool:
        """Проверяет, включена ли капча."""
        return settings.SMARTCAPTCHA_ENABLED


captcha_validator = CaptchaValidator()


