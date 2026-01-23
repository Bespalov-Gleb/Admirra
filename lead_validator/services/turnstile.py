"""
Заглушка для Cloudflare Turnstile CAPTCHA.
Реальная интеграция будет добавлена позже.

Для активации:
1. Получите ключи на https://dash.cloudflare.com
2. Добавьте TURNSTILE_SECRET_KEY в .env
3. Установите TURNSTILE_ENABLED=true
"""

import logging
import httpx
from typing import Optional
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.turnstile")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileValidator:
    """
    Валидатор Cloudflare Turnstile CAPTCHA.
    Пока работает как заглушка - всегда пропускает.
    """
    
    def __init__(self):
        self.secret_key = settings.TURNSTILE_SECRET_KEY
        self.enabled = settings.TURNSTILE_ENABLED
        
    async def validate(
        self, 
        token: Optional[str], 
        remote_ip: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Проверка Turnstile токена.
        
        Args:
            token: cf-turnstile-response из формы
            remote_ip: IP клиента для дополнительной проверки
            
        Returns:
            (is_valid, error_message)
        """
        # Если отключён — пропускаем всех
        if not self.enabled:
            logger.debug("Turnstile disabled, skipping validation")
            return True, ""
            
        # Если нет секретного ключа — пропускаем с предупреждением
        if not self.secret_key:
            logger.warning("Turnstile enabled but no secret key configured")
            return True, ""
            
        # Если нет токена — отклоняем
        if not token:
            logger.info("Turnstile token missing")
            return False, "captcha_missing"
            
        # Проверяем токен через API Cloudflare
        try:
            data = {
                "secret": self.secret_key,
                "response": token
            }
            
            if remote_ip:
                data["remoteip"] = remote_ip
                
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(TURNSTILE_VERIFY_URL, data=data)
                result = response.json()
                
                if result.get("success"):
                    logger.info(f"Turnstile validation passed for IP: {remote_ip}")
                    return True, ""
                else:
                    error_codes = result.get("error-codes", ["unknown"])
                    logger.info(f"Turnstile validation failed: {error_codes}")
                    return False, f"captcha_invalid:{','.join(error_codes)}"
                    
        except httpx.TimeoutException:
            logger.warning("Turnstile API timeout")
            # Fail-open: пропускаем при таймауте
            return True, ""
            
        except Exception as e:
            logger.error(f"Turnstile validation error: {e}")
            # Fail-open: пропускаем при ошибках
            return True, ""


# Глобальный экземпляр
turnstile_validator = TurnstileValidator()

