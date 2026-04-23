"""
Webhook роутер для интеграции с Tilda и Marquiz.
Преобразует данные из форм/квизов в формат LeadInput и передаёт на валидацию.
Также поддерживает webhook для проектов телефонии.
"""

import logging
import re
import json
import uuid
import os
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Depends, Body, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, model_validator
from lead_validator.schemas import LeadInput, ValidationResult
from lead_validator.validators import lead_validator
from core.database import get_db
from core import models

logger = logging.getLogger("lead_validator.webhook")

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean env var values like true/1/yes/on."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


# If false -> не проверяем webhook_secret для эндпоинта телефонии `/webhook/phone/{project_id}`.
# Это удобно, когда сторонняя система (Marquiz) может передать только URL без заголовков.
PHONE_WEBHOOK_SECRET_CHECK_ENABLED = _env_bool("PHONE_WEBHOOK_SECRET_CHECK_ENABLED", True)


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
    
    Поддерживаем оба формата:
    - Плоский: name, phone, email, utm_source, ... на верхнем уровне
    - Вложенный (официальный): contacts.phone, contacts.email, extra.utm, extra.ip
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

    @model_validator(mode="before")
    @classmethod
    def flatten_marquiz_format(cls, data: Any) -> Any:
        """Извлекаем phone, email, name из contacts и UTM из extra при вложенном формате."""
        if not isinstance(data, dict):
            return data
        contacts = data.get("contacts") or {}
        extra = data.get("extra") or {}
        utm = extra.get("utm") or {}
        # Если на верхнем уровне нет phone — берём из contacts
        if not data.get("phone") and contacts.get("phone"):
            data = {**data, "phone": contacts.get("phone")}
        if not data.get("email") and contacts.get("email"):
            data = {**data, "email": contacts.get("email")}
        if not data.get("name") and contacts.get("name"):
            data = {**data, "name": contacts.get("name")}
        # UTM из extra.utm
        if not data.get("utm_source") and utm.get("source"):
            data = {**data, "utm_source": utm.get("source")}
        if not data.get("utm_medium") and utm.get("medium"):
            data = {**data, "utm_medium": utm.get("medium")}
        if not data.get("utm_campaign") and utm.get("campaign"):
            data = {**data, "utm_campaign": utm.get("campaign")}
        if not data.get("utm_content") and utm.get("content"):
            data = {**data, "utm_content": utm.get("content")}
        if not data.get("utm_term") and utm.get("term"):
            data = {**data, "utm_term": utm.get("term")}
        # IP и timezone из extra
        if not data.get("IP") and extra.get("ip"):
            data = {**data, "IP": extra.get("ip")}
        if not data.get("leadTimezone") and extra.get("timezone") is not None:
            data = {**data, "leadTimezone": str(extra.get("timezone"))}
        if not data.get("referrer") and extra.get("referrer"):
            data = {**data, "referrer": extra.get("referrer")}
        # quiz в Marquiz — объект {id, name}; приводим к строке для совместимости
        quiz_val = data.get("quiz")
        if isinstance(quiz_val, dict):
            data = {**data, "quiz": quiz_val.get("name") or str(quiz_val.get("id", ""))}
        return data


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


def _parse_marquiz_timezone(tz: Any) -> Optional[str]:
    """
    Marquiz extra.timezone — число (UTC offset, напр. 3, 5, 10).
    Преобразуем в строку и вызываем parse_timezone_offset.
    """
    if tz is None:
        return None
    if isinstance(tz, (int, float)):
        return parse_timezone_offset(f"UTC {int(tz)}")
    if isinstance(tz, str):
        return parse_timezone_offset(tz)
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
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    secret: Optional[str] = None
) -> ValidationResult:
    """Обработка webhook для проекта телефонии"""
    project = None

    # 1) Пытаемся интерпретировать как UUID проекта
    try:
        project_uuid = uuid.UUID(project_id)
        project = db.query(models.PhoneProject).filter(
            models.PhoneProject.id == project_uuid,
            models.PhoneProject.is_active == True
        ).first()
    except ValueError:
        project = None

    # 2) Фоллбек: ищем по сохраненному webhook_url (для legacy URL)
    if project is None:
        webhook_path = f"/webhook/phone/{project_id}"
        project = db.query(models.PhoneProject).filter(
            models.PhoneProject.webhook_url == webhook_path,
            models.PhoneProject.is_active == True
        ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Phone project not found or inactive")

    # project_uuid для передачи в validate (при fallback по webhook_url project_uuid мог быть не задан)
    project_uuid = project.id

    # Проверяем секрет (header или query)
    provided_secret = request.headers.get("x-webhook-secret") or secret
    if project.webhook_secret and PHONE_WEBHOOK_SECRET_CHECK_ENABLED:
        if not provided_secret or provided_secret != project.webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # Извлекаем основные поля (поддерживаем плоский формат и вложенный Marquiz: contacts, extra)
    contacts = data.get("contacts") or {}
    phone = (
        data.get("phone") or data.get("Phone") or data.get("PHONE")
        or contacts.get("phone") or contacts.get("Phone")
    )
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    logger.info(f"Phone project webhook received: project={project.name}, phone={phone}")
    
    email = (
        data.get("email") or data.get("Email") or data.get("EMAIL")
        or contacts.get("email") or contacts.get("Email")
    )
    name = (
        data.get("name") or data.get("Name") or data.get("NAME")
        or contacts.get("name") or contacts.get("Name")
    )
    
    # UTM: из плоских полей, extra.utm (Marquiz) или referer
    extra = data.get("extra") or {}
    utm_extra = extra.get("utm") or {}
    referer = request.headers.get("referer") or extra.get("referrer") or extra.get("href") or ""
    utm_from_ref = extract_utm_from_url(referer)
    utm_source = (
        data.get("utm_source") or utm_extra.get("source") or utm_from_ref.get("utm_source")
    )
    utm_medium = (
        data.get("utm_medium") or utm_extra.get("medium") or utm_from_ref.get("utm_medium")
    )
    utm_campaign = (
        data.get("utm_campaign") or utm_extra.get("campaign") or utm_from_ref.get("utm_campaign")
    )
    utm_content = (
        data.get("utm_content") or utm_extra.get("content") or utm_from_ref.get("utm_content")
    )
    utm_term = (
        data.get("utm_term") or utm_extra.get("term") or utm_from_ref.get("utm_term")
    )
    
    # Токен CAPTCHA: из разных вариантов названий (Marquiz, Tilda, Turnstile, reCAPTCHA, SmartCaptcha)
    captcha_token = (
        data.get("smart_token") or data.get("smartcaptcha_token")
        or data.get("cf-turnstile-response") or data.get("cf_turnstile_response")
        or data.get("g-recaptcha-response") or data.get("g_recaptcha_response")
        or contacts.get("smart_token") or (extra.get("captcha") if isinstance(extra.get("captcha"), str) else None)
    )
    
    # Преобразуем в LeadInput
    lead = LeadInput(
        phone=phone,
        email=email,
        name=name,
        smart_token=captcha_token,
        js_token=data.get("js_token"),
        timestamp=data.get("timestamp"),
        honeypot=data.get("honeypot"),
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        ym_uid=data.get("ym_uid") or data.get("_ym_uid"),
        browser_timezone=(
            data.get("browser_timezone") or data.get("timezone")
            or _parse_marquiz_timezone(extra.get("timezone"))
        ),
    )
    
    # IP: из extra (Marquiz) или из запроса
    client_ip = extra.get("ip") or _get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    
    # Валидируем с сохранением в базу.
    # Для server-to-server webhook отключаем антибот-поля формы (js_token/timestamp/honeypot),
    # т.к. внешние сервисы (Marquiz/Tilda) обычно их не передают.
    result = await lead_validator.validate(
        lead, 
        client_ip=client_ip,
        user_agent=user_agent,
        referer=referer,
        project_id=project_uuid,
        db=db,
        form_data=data,  # Сохраняем все данные формы
        skip_request_validation=True,
        skip_antibot_validation=True,
    )
    
    logger.info(f"Phone project lead result: success={result.success}, phone={phone}")
    return result


@router.get(
    "/info",
    summary="Информация о webhook эндпоинтах",
    description="Возвращает URL-ы для настройки в Tilda и Marquiz"
)
async def webhook_info(request: Request) -> Dict[str, Any]:
    """Информация о доступных webhook эндпоинтах (роутер подключён с prefix=/api)."""
    base_url = str(request.base_url).rstrip("/")
    webhook_base = f"{base_url}/api/webhook"
    return {
        "endpoints": {
            "tilda": f"{webhook_base}/tilda/",
            "marquiz": f"{webhook_base}/marquiz/",
            "phone_project": f"{webhook_base}/phone/{{project_id}}",
            "debug_tilda": f"{webhook_base}/debug/tilda/",
            "debug_marquiz": f"{webhook_base}/debug/marquiz/",
        },
        "tilda_setup": {
            "step1": "Настройки сайта → Формы → Webhook (или в блоке формы: Контент → Webhook)",
            "step2": "Укажите URL вашего проекта (см. вкладку Webhook в проекте телефонии)",
            "step3": "Формат: JSON. Для проекта укажите URL вида .../api/webhook/phone/{project_id} и заголовок X-Webhook-Secret",
            "step4": "Переопубликуйте страницу с формой",
        },
        "marquiz_setup": {
            "step1": "Редактор квиза → Интеграции → Webhook (или Настройки → Интеграции)",
            "step2": "Укажите URL проекта: .../api/webhook/phone/{project_id}",
            "step3": "Добавьте заголовок X-Webhook-Secret со значением секрета проекта",
            "step4": "Сохраните настройки. Заявки пойдут в квалификацию этого проекта.",
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

