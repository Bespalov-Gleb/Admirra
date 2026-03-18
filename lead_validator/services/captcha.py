"""
Сервис валидации капчи.
Поддерживает:
- Cloudflare Turnstile (рекомендуется)
- Google reCAPTCHA v2/v3
- Yandex SmartCaptcha
"""

import logging
import httpx
from typing import Tuple, Optional
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.captcha")

# API endpoints для разных провайдеров капчи
CLOUDFLARE_TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
YANDEX_SMARTCAPTCHA_URL = "https://smartcaptcha.yandexcloud.net/validate"


async def validate_turnstile(token: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Проверяет токен Cloudflare Turnstile.
    
    Документация: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
    
    Args:
        token: Токен капчи от клиента
        client_ip: IP адрес клиента
    
    Returns:
        Tuple[bool, str]: (успех, сообщение об ошибке)
    """
    if not settings.TURNSTILE_SECRET_KEY:
        logger.warning("Turnstile secret key not set")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: configuration error"
    
    if not token:
        return False, "CAPTCHA: token required"
    
    try:
        payload = {
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
        }
        if client_ip:
            payload["remoteip"] = client_ip
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(CLOUDFLARE_TURNSTILE_URL, data=payload)
            data = response.json()
        
        logger.debug(f"Turnstile response: {data}")
        
        if data.get("success"):
            logger.info("Turnstile validation passed")
            return True, ""
        else:
            errors = data.get("error-codes", [])
            message = ", ".join(errors) if errors else "validation failed"
            logger.warning(f"Turnstile validation failed: {message}")
            return False, f"CAPTCHA: {message}"
            
    except httpx.TimeoutException:
        logger.error("Turnstile API timeout")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: service timeout"
        
    except Exception as e:
        logger.error(f"Turnstile error: {e}")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, f"CAPTCHA: service error"


async def validate_recaptcha(token: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Проверяет токен Google reCAPTCHA v2/v3.
    
    Документация: https://developers.google.com/recaptcha/docs/verify
    
    Args:
        token: Токен капчи от клиента
        client_ip: IP адрес клиента
    
    Returns:
        Tuple[bool, str]: (успех, сообщение об ошибке)
    """
    if not settings.RECAPTCHA_SECRET_KEY:
        logger.warning("reCAPTCHA secret key not set")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: configuration error"
    
    if not token:
        return False, "CAPTCHA: token required"
    
    try:
        payload = {
            "secret": settings.RECAPTCHA_SECRET_KEY,
            "response": token,
        }
        if client_ip:
            payload["remoteip"] = client_ip
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(RECAPTCHA_VERIFY_URL, data=payload)
            data = response.json()
        
        logger.debug(f"reCAPTCHA response: {data}")
        
        if data.get("success"):
            # Для reCAPTCHA v3 можно проверить score
            score = data.get("score", 1.0)
            if score < settings.RECAPTCHA_MIN_SCORE:
                logger.warning(f"reCAPTCHA score too low: {score}")
                return False, f"CAPTCHA: low score ({score})"
            
            logger.info(f"reCAPTCHA validation passed (score: {score})")
            return True, ""
        else:
            errors = data.get("error-codes", [])
            message = ", ".join(errors) if errors else "validation failed"
            logger.warning(f"reCAPTCHA validation failed: {message}")
            return False, f"CAPTCHA: {message}"
            
    except httpx.TimeoutException:
        logger.error("reCAPTCHA API timeout")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: service timeout"
        
    except Exception as e:
        logger.error(f"reCAPTCHA error: {e}")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, f"CAPTCHA: service error"


async def validate_smartcaptcha(token: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
    """
    Проверяет токен Yandex SmartCaptcha.
    
    Документация: https://cloud.yandex.ru/docs/smartcaptcha/
    
    Args:
        token: Токен капчи (smart-token) от клиента
        client_ip: IP адрес клиента
    
    Returns:
        Tuple[bool, str]: (успех, сообщение об ошибке)
    """
    if not settings.SMARTCAPTCHA_SERVER_KEY:
        logger.warning("SmartCaptcha server key not set")
        if settings.FAIL_OPEN_MODE:
            return True, ""
        return False, "CAPTCHA: configuration error"
    
    if not token:
        return False, "CAPTCHA: token required"
    
    try:
        params = {
            "secret": settings.SMARTCAPTCHA_SERVER_KEY,
            "token": token,
        }
        if client_ip:
            params["ip"] = client_ip
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(YANDEX_SMARTCAPTCHA_URL, params=params)
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
    """
    Универсальный класс для валидации капчи.
    Поддерживает Cloudflare Turnstile, Google reCAPTCHA и Yandex SmartCaptcha.
    """
    
    async def validate(self, token: str, client_ip: Optional[str] = None) -> Tuple[bool, str]:
        """
        Валидация токена капчи через выбранный провайдер.
        
        Провайдер определяется автоматически по наличию ключей в настройках:
        1. Приоритет: Cloudflare Turnstile (если есть TURNSTILE_SECRET_KEY)
        2. Затем: Google reCAPTCHA (если есть RECAPTCHA_SECRET_KEY)
        3. Затем: Yandex SmartCaptcha (если есть SMARTCAPTCHA_SERVER_KEY)
        """
        # Проверяем, включена ли капча вообще
        if not self.is_enabled():
            logger.debug("CAPTCHA disabled globally, skipping validation")
            return True, ""
        
        # Определяем провайдера по наличию ключей
        if settings.TURNSTILE_SECRET_KEY:
            logger.debug("Using Cloudflare Turnstile")
            return await validate_turnstile(token, client_ip)
        
        elif settings.RECAPTCHA_SECRET_KEY:
            logger.debug("Using Google reCAPTCHA")
            return await validate_recaptcha(token, client_ip)
        
        elif settings.SMARTCAPTCHA_SERVER_KEY:
            logger.debug("Using Yandex SmartCaptcha")
            return await validate_smartcaptcha(token, client_ip)
        
        else:
            logger.warning("No CAPTCHA provider configured!")
            if settings.FAIL_OPEN_MODE:
                return True, ""
            return False, "CAPTCHA: no provider configured"
    
    def is_enabled(self) -> bool:
        """
        Проверяет, включена ли капча.
        CAPTCHA_ENABLED=false в .env отключает проверку.
        Иначе капча включена, если настроен хотя бы один провайдер.
        """
        if not getattr(settings, "CAPTCHA_ENABLED", True):
            return False
        return bool(
            settings.TURNSTILE_SECRET_KEY or
            settings.RECAPTCHA_SECRET_KEY or
            settings.SMARTCAPTCHA_SERVER_KEY
        )
    
    def get_provider_name(self) -> str:
        """Возвращает имя текущего провайдера капчи."""
        if settings.TURNSTILE_SECRET_KEY:
            return "Cloudflare Turnstile"
        elif settings.RECAPTCHA_SECRET_KEY:
            return "Google reCAPTCHA"
        elif settings.SMARTCAPTCHA_SERVER_KEY:
            return "Yandex SmartCaptcha"
        return "None"


captcha_validator = CaptchaValidator()
