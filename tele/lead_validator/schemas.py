"""
Pydantic модели для валидации входящих данных и ответов API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


class LeadInput(BaseModel):
    """
    Входящие данные лида с веб-формы.
    Поддерживает антибот-поля и UTM-метки.
    """
    # Основные данные
    phone: str = Field(..., description="Номер телефона (обязательное поле)")
    email: Optional[str] = Field(None, description="Email адрес")
    name: Optional[str] = Field(None, description="ФИО клиента")
    
    # Антибот поля
    timestamp: Optional[int] = Field(
        None, 
        description="Unix timestamp начала заполнения формы"
    )
    honeypot: Optional[str] = Field(
        None, 
        description="Скрытое поле-ловушка, должно быть пустым"
    )
    cf_turnstile_response: Optional[str] = Field(
        None,
        description="Токен Cloudflare Turnstile CAPTCHA (устарело)"
    )
    smart_token: Optional[str] = Field(
        None,
        description="Токен Yandex SmartCaptcha"
    )
    
    # UTM метки для аналитики
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    
    # Geo данные (заполняются сервером)
    client_ip: Optional[str] = None
    geo_country: Optional[str] = None  # Код страны (RU, UA, etc.)
    
    # Яндекс.Метрика client ID (cookie _ym_uid)
    ym_uid: Optional[str] = None
    
    # Timezone браузера (Intl.DateTimeFormat().resolvedOptions().timeZone)
    browser_timezone: Optional[str] = Field(
        None,
        description="Часовой пояс браузера клиента"
    )
    
    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Удаляет лишние символы из телефона, оставляя только цифры и +"""
        if not v:
            return v
        # Убираем всё кроме цифр и +
        cleaned = re.sub(r"[^\d+]", "", v)
        return cleaned


class DaDataPhoneResponse(BaseModel):
    """
    Ответ DaData Clean API для телефона.
    Полная структура согласно документации.
    """
    source: str = Field(..., description="Исходный телефон")
    type: Optional[str] = Field(None, description="Тип: Мобильный, Стационарный")
    phone: Optional[str] = Field(None, description="Стандартизованный телефон")
    country_code: Optional[str] = Field(None, description="Код страны")
    city_code: Optional[str] = Field(None, description="Код города / DEF-код")
    number: Optional[str] = Field(None, description="Локальный номер")
    extension: Optional[str] = Field(None, description="Добавочный номер")
    provider: Optional[str] = Field(None, description="Оператор связи")
    country: Optional[str] = Field(None, description="Страна")
    region: Optional[str] = Field(None, description="Регион")
    city: Optional[str] = Field(None, description="Город")
    timezone: Optional[str] = Field(None, description="Часовой пояс")
    qc_conflict: int = Field(0, description="Признак конфликта с адресом")
    qc: int = Field(1, description="Код качества: 0=OK, 1=допущения, 2=мусор")


class ValidationResult(BaseModel):
    """
    Результат валидации лида.
    Возвращается клиенту после обработки.
    """
    success: bool = Field(..., description="Лид прошёл валидацию")
    lead_id: Optional[str] = Field(None, description="ID созданного лида")
    rejection_reason: Optional[str] = Field(
        None, 
        description="Причина отклонения если success=False"
    )
    execution_time_ms: float = Field(..., description="Время обработки в мс")
    
    # Детали валидации (для отладки)
    phone_type: Optional[str] = Field(None, description="Тип телефона")
    phone_provider: Optional[str] = Field(None, description="Оператор")
    phone_region: Optional[str] = Field(None, description="Регион телефона")
    dadata_qc: Optional[int] = Field(None, description="Код качества DaData")


class RejectedLead(BaseModel):
    """
    Структура для логирования отклонённых заявок.
    Сохраняется в Airtable или локальную БД.
    """
    phone: str
    email: Optional[str] = None
    name: Optional[str] = None
    rejection_reason: str
    rejection_details: Optional[str] = None
    
    # UTM для анализа источников мусора
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    
    # Мета
    client_ip: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # DaData данные если были получены
    dadata_qc: Optional[int] = None
    phone_type: Optional[str] = None
