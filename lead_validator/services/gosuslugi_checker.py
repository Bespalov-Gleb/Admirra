"""
Проверка регистрации телефона в Госуслугах через внешний провайдер.

Интеграция настраивается через env:
- GOSUSLUGI_API_URL
- GOSUSLUGI_API_KEY
- GOSUSLUGI_TIMEOUT

Ожидаемый формат ответа (любой из вариантов полей):
{
  "registered": true,
  "name": "Иван",
  "surname": "Иванов",
  "middle_name": "Иванович"
}
"""

import logging
from typing import Optional
from dataclasses import dataclass

import httpx
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.gosuslugi_checker")


@dataclass
class GosuslugiCheckResult:
    """Результат проверки регистрации в Госуслугах"""
    phone: str
    has_registration: Optional[bool] = None  # Есть ли регистрация
    name: Optional[str] = None  # Имя из Госуслуг
    surname: Optional[str] = None  # Фамилия из Госуслуг
    middle_name: Optional[str] = None  # Отчество (если доступно)
    
    # Статус проверки
    checked: bool = False
    error: Optional[str] = None


class GosuslugiChecker:
    """
    Проверка регистрации телефона в Госуслугах.
    
    ВАЖНО: Это заглушка. Для реальной проверки нужно:
    1. Выбрать провайдера API (официальный API Госуслуг или сторонний сервис)
    2. Получить API ключи и доступ
    3. Реализовать вызовы конкретного API
    
    Проверка Госуслуг позволяет:
    - Подтвердить реальность пользователя
    - Получить ФИО для обогащения данных
    - Повысить качество лида
    """
    
    def __init__(self):
        self.api_url = settings.GOSUSLUGI_API_URL
        self.api_key = settings.GOSUSLUGI_API_KEY
        self.timeout = settings.GOSUSLUGI_TIMEOUT
        self.enabled = bool(self.api_url and self.api_key)
        
    async def check(self, phone: str) -> GosuslugiCheckResult:
        """
        Проверяет регистрацию телефона в Госуслугах.
        
        Args:
            phone: Номер телефона в любом формате
            
        Returns:
            GosuslugiCheckResult с результатами проверки
        """
        result = GosuslugiCheckResult(phone=phone)
        
        if not self.enabled:
            result.error = "Gosuslugi checker not configured"
            logger.debug(f"Gosuslugi check skipped for {phone}: not configured")
            return result

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"phone": phone}
                )

                if response.status_code == 200:
                    data = response.json() or {}
                    registered = data.get("registered")
                    if registered is None:
                        registered = data.get("has_registration")
                    result.has_registration = bool(registered)
                    if result.has_registration:
                        result.name = data.get("name") or data.get("first_name")
                        result.surname = data.get("surname") or data.get("last_name")
                        result.middle_name = data.get("middle_name")
                    result.checked = True
                else:
                    result.error = f"gosuslugi_http_{response.status_code}"
                    logger.warning(f"Gosuslugi API error: {response.status_code} - {response.text[:200]}")
        except httpx.TimeoutException:
            result.error = "gosuslugi_timeout"
            logger.warning(f"Gosuslugi timeout for {phone}")
        except Exception as e:
            result.error = "gosuslugi_error"
            logger.error(f"Gosuslugi unexpected error: {e}")

        return result


# Глобальный экземпляр
gosuslugi_checker = GosuslugiChecker()


