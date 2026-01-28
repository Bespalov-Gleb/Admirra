"""
Webhook роутер для интеграции с Tilda и Marquiz.
Преобразует данные из форм/квизов в формат LeadInput и передаёт на валидацию.
Также поддерживает webhook для проектов телефонии.
"""

import logging
import re
import json
import uuid
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from lead_validator.schemas import LeadInput, ValidationResult
from lead_validator.validators import lead_validator
from core.database import get_db
from core import models

logger = logging.getLogger("lead_validator.webhook")

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


# ============================================================================
# Tilda Schema
# ============================================================================

class TildaWebhookData(BaseModel):
    """
    Данные от Tilda форм.
    
    Поля из CSV:
    - created, name, phone, firm, cash, city, checkbox
    - formid, formname, referer (с UTM параметрами)
    - is_favorite, note
    """
    # Основные поля
    name: Optional[str] = None
    phone: str = Field(..., description="Телефон (обязательно)")
    email: Optional[str] = None
    
    # Дополнительные поля формы
    firm: Optional[str] = None
    cash: Optional[str] = None
    city: Optional[str] = None
    checkbox: Optional[str] = None
    
    # Метаданные формы
    formid: Optional[str] = None
    formname: Optional[str] = None
    referer: Optional[str] = None
    
    # Служебные
    created: Optional[str] = None
    is_favorite: Optional[str] = None
    note: Optional[str] = None
    
    class Config:
        extra = "allow"  # Разрешаем дополнительные поля


# ============================================================================
# Marquiz Schema
# ============================================================================

class MarquizWebhookData(BaseModel):
    """
    Данные от Marquiz квизов.
    
    Поля из CSV (разделитель - точка с запятой):
    - name, phone, email, address, customField
    - created, created_formatted, source (URL с UTM)
    - marketingConsent, referrer, location, leadTimezone
    - IP, userAgent, verified, captchaVerified
    - variant, quiz
    - Динамические поля ответов на вопросы
    - utm_source, utm_medium, utm_campaign, utm_term, utm_content
    - Мессенджеры: telegram, vk, whatsapp, viber, skype и др.
    - fingerprint, _ym_uid и др. tracking параметры
    """
    # Основные поля
    name: Optional[str] = None
    phone: str = Field(..., description="Телефон (обязательно)")
    email: Optional[str] = None
    address: Optional[str] = None
    customField: Optional[str] = None
    
    # Временные метки
    created: Optional[str] = None
    created_formatted: Optional[str] = None
    
    # Источник и UTM
    source: Optional[str] = None  # URL с UTM параметрами
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    
    # Geo и браузер
    location: Optional[str] = None  # "Россия, Москва"
    leadTimezone: Optional[str] = None  # "UTC 3"
    IP: Optional[str] = None
    userAgent: Optional[str] = None
    
    # Верификация
    verified: Optional[str] = None
    captchaVerified: Optional[str] = None
    marketingConsent: Optional[str] = None
    
    # Квиз
    variant: Optional[str] = None
    quiz: Optional[str] = None
    result: Optional[str] = None
    
    # Мессенджеры
    telegram: Optional[str] = None
    vk: Optional[str] = None
    whatsapp: Optional[str] = None
    viber: Optional[str] = None
    skype: Optional[str] = None
    
    # Tracking
    fingerprint: Optional[str] = None
    ym_uid: Optional[str] = Field(None, description="Яндекс.Метрика client ID")
    
    class Config:
        extra = "allow"  # Разрешаем динамические поля (ответы на вопросы)
        populate_by_name = True


# ============================================================================
# Helper Functions
# ============================================================================

def extract_utm_from_url(url: str) -> Dict[str, Optional[str]]:
    """Извлекает UTM параметры из URL."""
    result = {
        "utm_source": None,
        "utm_medium": None,
        "utm_campaign": None,
        "utm_content": None,
        "utm_term": None,
    }
    
    if not url:
        return result
    
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        for key in result.keys():
            if key in params:
                result[key] = params[key][0]
    except Exception as e:
        logger.warning(f"Failed to parse URL for UTM: {e}")
    
    return result


def extract_country_from_location(location: str) -> Optional[str]:
    """
    Извлекает код страны из строки локации.
    Например: "Россия, Москва" → "RU"
    """
    if not location:
        return None
    
    country_map = {
        "россия": "RU",
        "russia": "RU",
        "украина": "UA",
        "ukraine": "UA",
        "беларусь": "BY",
        "belarus": "BY",
        "казахстан": "KZ",
        "kazakhstan": "KZ",
    }
    
    location_lower = location.lower()
    for country_name, code in country_map.items():
        if country_name in location_lower:
            return code
    
    return None


def parse_timezone_offset(tz_str: str) -> Optional[str]:
    """
    Преобразует строку типа "UTC 3" или "UTC 10" в IANA timezone.
    """
    if not tz_str:
        return None
    
    # Пример: "UTC 3" → "Europe/Moscow" (приблизительно)
    match = re.search(r"UTC\s*([+-]?\d+)", tz_str)
    if match:
        offset = int(match.group(1))
        # Простое сопоставление для России
        if offset == 3:
            return "Europe/Moscow"
        elif offset == 5:
            return "Asia/Yekaterinburg"
        elif offset == 7:
            return "Asia/Krasnoyarsk"
        elif offset == 10:
            return "Asia/Vladivostok"
    
    return None


# ============================================================================
# Tilda Webhook Endpoint
# ============================================================================

@router.post(
    "/tilda/",
    response_model=ValidationResult,
    summary="Webhook для Tilda форм",
    description="""
    Принимает данные от Tilda webhook.
    
    Настройка в Tilda:
    1. Форма → Настройки → Webhook
    2. URL: https://your-domain.com/webhook/tilda/
    3. Формат: JSON
    """
)
async def tilda_webhook(data: TildaWebhookData, request: Request) -> ValidationResult:
    """Обработка webhook от Tilda."""
    logger.info(f"Tilda webhook received: phone={data.phone}, form={data.formid}")
    
    # Извлекаем UTM из referer
    utm = extract_utm_from_url(data.referer or "")
    
    # Преобразуем в LeadInput
    lead = LeadInput(
        phone=data.phone,
        email=data.email,
        name=data.name,
        utm_source=utm.get("utm_source"),
        utm_medium=utm.get("utm_medium"),
        utm_campaign=utm.get("utm_campaign"),
        utm_content=utm.get("utm_content"),
        utm_term=utm.get("utm_term"),
    )
    
    # Получаем IP клиента
    client_ip = _get_client_ip(request)
    
    # Валидируем
    result = await lead_validator.validate(lead, client_ip)
    
    logger.info(f"Tilda lead result: success={result.success}, phone={data.phone}")
    return result


# ============================================================================
# Marquiz Webhook Endpoint
# ============================================================================

@router.post(
    "/marquiz/",
    response_model=ValidationResult,
    summary="Webhook для Marquiz квизов",
    description="""
    Принимает данные от Marquiz webhook.
    
    Настройка в Marquiz:
    1. Интеграции → Webhook
    2. URL: https://your-domain.com/webhook/marquiz/
    3. Формат: JSON
    """
)
async def marquiz_webhook(data: MarquizWebhookData, request: Request) -> ValidationResult:
    """Обработка webhook от Marquiz."""
    logger.info(f"Marquiz webhook received: phone={data.phone}, quiz={data.quiz}")
    
    # UTM может быть в отдельных полях или в source URL
    utm_source = data.utm_source
    utm_medium = data.utm_medium
    utm_campaign = data.utm_campaign
    utm_content = data.utm_content
    utm_term = data.utm_term
    
    # Если UTM пусто, пробуем извлечь из source URL
    if not utm_source and data.source:
        utm_from_url = extract_utm_from_url(data.source)
        utm_source = utm_source or utm_from_url.get("utm_source")
        utm_medium = utm_medium or utm_from_url.get("utm_medium")
        utm_campaign = utm_campaign or utm_from_url.get("utm_campaign")
        utm_content = utm_content or utm_from_url.get("utm_content")
        utm_term = utm_term or utm_from_url.get("utm_term")
    
    # Определяем страну из location
    geo_country = extract_country_from_location(data.location)
    
    # Преобразуем timezone
    browser_timezone = parse_timezone_offset(data.leadTimezone)
    
    # Преобразуем в LeadInput
    lead = LeadInput(
        phone=data.phone,
        email=data.email,
        name=data.name,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        client_ip=data.IP,
        geo_country=geo_country,
        browser_timezone=browser_timezone,
        ym_uid=data.ym_uid,
    )
    
    # IP: используем из данных или из запроса
    client_ip = data.IP or _get_client_ip(request)
    
    # User-Agent из данных
    user_agent = data.userAgent
    
    # Валидируем
    result = await lead_validator.validate(
        lead, 
        client_ip=client_ip,
        user_agent=user_agent,
        referer=data.referrer
    )
    
    logger.info(f"Marquiz lead result: success={result.success}, phone={data.phone}")
    return result


# ============================================================================
# Info Endpoint
# ============================================================================

# ============================================================================
# Phone Project Webhook Endpoint
# ============================================================================

@router.post(
    "/phone/{project_id}",
    response_model=ValidationResult,
    summary="Webhook для проекта телефонии",
    description="""
    Принимает данные заявки для конкретного проекта телефонии.
    
    URL формируется автоматически при создании проекта:
    /api/webhook/phone/{project_id}
    
    Поддерживает любые данные формы (Tilda, Marquiz, кастомные формы).
    """
)
async def phone_project_webhook(
    project_id: str,
    data: dict,
    request: Request,
    db: Session = Depends(get_db)
) -> ValidationResult:
    """Обработка webhook для проекта телефонии"""
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")
    
    # Находим проект
    project = db.query(models.PhoneProject).filter(
        models.PhoneProject.id == project_uuid,
        models.PhoneProject.is_active == True
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Phone project not found or inactive")
    
    logger.info(f"Phone project webhook received: project={project.name}, phone={data.get('phone')}")
    
    # Извлекаем основные поля (поддерживаем разные форматы)
    phone = data.get("phone") or data.get("Phone") or data.get("PHONE")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    
    email = data.get("email") or data.get("Email") or data.get("EMAIL")
    name = data.get("name") or data.get("Name") or data.get("NAME")
    
    # Извлекаем UTM из данных или referer
    referer = request.headers.get("referer", "")
    utm = extract_utm_from_url(referer)
    utm_source = data.get("utm_source") or utm.get("utm_source")
    utm_medium = data.get("utm_medium") or utm.get("utm_medium")
    utm_campaign = data.get("utm_campaign") or utm.get("utm_campaign")
    utm_content = data.get("utm_content") or utm.get("utm_content")
    utm_term = data.get("utm_term") or utm.get("utm_term")
    
    # Преобразуем в LeadInput
    lead = LeadInput(
        phone=phone,
        email=email,
        name=name,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        ym_uid=data.get("ym_uid") or data.get("_ym_uid"),
        browser_timezone=data.get("browser_timezone") or data.get("timezone")
    )
    
    # Получаем IP клиента
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    
    # Валидируем с сохранением в базу
    result = await lead_validator.validate(
        lead, 
        client_ip=client_ip,
        user_agent=user_agent,
        referer=referer,
        project_id=project_uuid,
        db=db,
        form_data=data  # Сохраняем все данные формы
    )
    
    logger.info(f"Phone project lead result: success={result.success}, phone={phone}")
    return result


@router.get(
    "/info",
    summary="Информация о webhook эндпоинтах",
    description="Возвращает URL-ы для настройки в Tilda и Marquiz"
)
async def webhook_info(request: Request) -> Dict[str, Any]:
    """Информация о доступных webhook эндпоинтах."""
    base_url = str(request.base_url).rstrip("/")
    
    return {
        "endpoints": {
            "tilda": f"{base_url}/webhook/tilda/",
            "marquiz": f"{base_url}/webhook/marquiz/",
            "debug_tilda": f"{base_url}/webhook/debug/tilda/",
            "debug_marquiz": f"{base_url}/webhook/debug/marquiz/",
        },
        "tilda_setup": {
            "step1": "Откройте настройки формы в Tilda",
            "step2": "Перейдите в раздел 'Подключить сервис' → 'Webhook'",
            "step3": f"Укажите URL: {base_url}/webhook/tilda/",
            "step4": "Выберите формат: JSON",
        },
        "marquiz_setup": {
            "step1": "Откройте настройки квиза в Marquiz",
            "step2": "Перейдите в 'Интеграции' → 'Webhook'",
            "step3": f"Укажите URL: {base_url}/webhook/marquiz/",
            "step4": "Сохраните настройки",
        }
    }


# ============================================================================
# Debug Endpoints - показывают что получаем и что отдаём
# ============================================================================

@router.post(
    "/debug/tilda/",
    summary="DEBUG: Тест Tilda webhook",
    description="""
    Отладочный эндпоинт для Tilda.
    
    Показывает:
    - Что получено (raw input)
    - Как преобразовано (parsed)
    - Что было бы отправлено на валидацию
    - Извлечённые UTM параметры
    
    НЕ отправляет на реальную валидацию!
    """
)
async def debug_tilda_webhook(data: TildaWebhookData, request: Request) -> Dict[str, Any]:
    """Debug webhook от Tilda - показывает что получаем."""
    
    # Извлекаем UTM из referer
    utm = extract_utm_from_url(data.referer or "")
    
    # Формируем LeadInput (как было бы)
    lead_data = {
        "phone": data.phone,
        "email": data.email,
        "name": data.name,
        "utm_source": utm.get("utm_source"),
        "utm_medium": utm.get("utm_medium"),
        "utm_campaign": utm.get("utm_campaign"),
        "utm_content": utm.get("utm_content"),
        "utm_term": utm.get("utm_term"),
    }
    
    return {
        "status": "DEBUG - данные НЕ отправлены на валидацию",
        "received": {
            "raw_fields": data.model_dump(exclude_none=True),
            "headers": {
                "content-type": request.headers.get("content-type"),
                "user-agent": request.headers.get("user-agent"),
                "x-forwarded-for": request.headers.get("x-forwarded-for"),
            },
            "client_ip": _get_client_ip(request),
        },
        "parsed": {
            "utm_from_referer": utm,
            "lead_input": lead_data,
        },
        "would_validate": {
            "endpoint": "/api/lead/",
            "checks": [
                "1. CAPTCHA (Yandex SmartCaptcha)",
                "2. Антибот (honeypot, timestamp)",
                "3. Формат телефона",
                "4. Rate Limiting",
                "5. Дедупликация",
                "6. DaData валидация",
                "7. UTM проверка"
            ]
        }
    }


@router.post(
    "/debug/marquiz/",
    summary="DEBUG: Тест Marquiz webhook",
    description="""
    Отладочный эндпоинт для Marquiz.
    
    Показывает:
    - Что получено (raw input)
    - Как преобразовано (parsed)
    - Извлечённые данные (geo, timezone, UTM)
    - Что было бы отправлено на валидацию
    
    НЕ отправляет на реальную валидацию!
    """
)
async def debug_marquiz_webhook(data: MarquizWebhookData, request: Request) -> Dict[str, Any]:
    """Debug webhook от Marquiz - показывает что получаем."""
    
    # UTM из полей или URL
    utm_source = data.utm_source
    utm_medium = data.utm_medium
    utm_campaign = data.utm_campaign
    utm_content = data.utm_content
    utm_term = data.utm_term
    
    utm_from_url = {}
    if not utm_source and data.source:
        utm_from_url = extract_utm_from_url(data.source)
        utm_source = utm_source or utm_from_url.get("utm_source")
        utm_medium = utm_medium or utm_from_url.get("utm_medium")
        utm_campaign = utm_campaign or utm_from_url.get("utm_campaign")
        utm_content = utm_content or utm_from_url.get("utm_content")
        utm_term = utm_term or utm_from_url.get("utm_term")
    
    # Geo и timezone
    geo_country = extract_country_from_location(data.location)
    browser_timezone = parse_timezone_offset(data.leadTimezone)
    
    # Формируем LeadInput
    lead_data = {
        "phone": data.phone,
        "email": data.email,
        "name": data.name,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
        "client_ip": data.IP,
        "geo_country": geo_country,
        "browser_timezone": browser_timezone,
        "ym_uid": data.ym_uid,
    }
    
    return {
        "status": "DEBUG - данные НЕ отправлены на валидацию",
        "received": {
            "raw_fields": data.model_dump(exclude_none=True),
            "headers": {
                "content-type": request.headers.get("content-type"),
                "user-agent": request.headers.get("user-agent"),
            },
            "client_ip_from_request": _get_client_ip(request),
            "client_ip_from_data": data.IP,
        },
        "parsed": {
            "utm_from_fields": {
                "source": data.utm_source,
                "medium": data.utm_medium,
                "campaign": data.utm_campaign,
            },
            "utm_from_url": utm_from_url,
            "utm_final": {
                "source": utm_source,
                "medium": utm_medium,
                "campaign": utm_campaign,
            },
            "geo": {
                "location": data.location,
                "country_code": geo_country,
            },
            "timezone": {
                "raw": data.leadTimezone,
                "parsed": browser_timezone,
            },
            "lead_input": lead_data,
        },
        "quiz_answers": {
            k: v for k, v in data.model_dump().items() 
            if k not in [
                "name", "phone", "email", "address", "customField",
                "created", "created_formatted", "source", "referrer",
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "location", "leadTimezone", "IP", "userAgent",
                "verified", "captchaVerified", "marketingConsent",
                "variant", "quiz", "result",
                "telegram", "vk", "whatsapp", "viber", "skype",
                "fingerprint", "ym_uid"
            ] and v is not None
        }
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _get_client_ip(request: Request) -> str:
    """Получить реальный IP клиента."""
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    
    # X-Forwarded-For
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    
    # X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback
    if request.client:
        return request.client.host
    
    return "unknown"

