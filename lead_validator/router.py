"""
FastAPI роутер для приёма лидов.
Основной эндпоинт: POST /api/lead/
"""

import logging
from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from lead_validator.schemas import LeadInput, ValidationResult
from lead_validator.validators import lead_validator
from lead_validator.services.trash_logger import trash_logger
from lead_validator.services.telegram import telegram_notifier
from lead_validator.services.analytics import analytics_service
from lead_validator.services.placement_blacklist import placement_blacklist
from core import models, security
from fastapi.responses import JSONResponse, Response
from datetime import datetime, timedelta
from datetime import date as Date, timezone
from typing import Optional, Literal
import uuid
from sqlalchemy.orm import Session
import sqlalchemy as sa
from core.database import get_db
from lead_validator.services.diagnostics import (
    diagnostic_admin, diagnostic_user, provider_probe, reserve_check,
)

logger = logging.getLogger("lead_validator.router")

router = APIRouter(tags=["Lead Validator"])



@router.post(
    "/lead/",
    response_model=ValidationResult,
    summary="Принять и валидировать лид",
    description="""
    Эндпоинт для приёма лидов с веб-форм.
    
    Проверки:
    1. Антибот (honeypot, timestamp)
    2. Качество данных (формат телефона)
    3. Rate Limiting по IP
    4. Дедупликация (проверка дубликатов)
    5. Валидация через DaData
    
    При успехе — уведомление в Telegram.
    При отклонении — запись в лог для аналитики.
    """
)
async def validate_lead(
    lead: LeadInput,
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: Optional[uuid.UUID] = None,
    secret: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ValidationResult:
    """
    Основной эндпоинт валидации лида.
    
    Принимает JSON с данными формы и возвращает результат валидации.
    Время обработки включено в ответ для мониторинга латентности.
    """
    from core.runtime import env_bool
    if env_bool('LEAD_DELIVERY_GUARDS', False):
        from lead_validator.services.webhook_scope import authorize
        bound = authorize(db, request, project_id, secret)
        return await lead_validator.validate(lead, client_ip=_get_client_ip(request),
            user_agent=request.headers.get('user-agent'), referer=request.headers.get('referer'),
            db=db, **bound)
    # Получаем реальный IP клиента
    client_ip = _get_client_ip(request)
    
    logger.info(f"New lead request from IP: {client_ip}, phone: {lead.phone}")
    
    # Выполняем валидацию
    result = await lead_validator.validate(lead, client_ip)
    
    return result


@router.get(
    "/lead/health",
    summary="Проверка работоспособности",
    description="Возвращает статус сервиса"
)
async def health_check():
    """Health check эндпоинт для мониторинга"""
    return {
        "status": "ok",
        "service": "lead_validator"
    }


@router.get(
    "/lead/stats",
    summary="Статистика отклонённых заявок",
    description="Возвращает статистику за указанную дату"
)
def get_stats(
    date: Optional[Date] = None,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Получить статистику отклонённых заявок.
    
    Args:
        date: Дата в формате YYYY-MM-DD (по умолчанию сегодня)
    """
    from lead_validator.services.scoped_stats import daily_rejections
    if date == Date.max:
        raise HTTPException(status_code=422, detail="Дата вне поддерживаемого диапазона")
    return daily_rejections(db, current_user.id, date or datetime.now(timezone.utc).date())


@router.get("/lead/test-telegram", summary="Проверить доступ к Telegram (без отправки)")
async def test_telegram(current_user=Depends(diagnostic_admin)):
    await reserve_check(current_user.id)
    return await provider_probe("telegram")


@router.get("/lead/test-captcha-api", summary="Проверить доступ к SmartCaptcha")
async def test_captcha_api(current_user=Depends(diagnostic_admin)):
    await reserve_check(current_user.id)
    return await provider_probe("captcha")


@router.get("/lead/test-metrica", summary="Проверить доступ к Метрике")
async def test_metrica(current_user=Depends(diagnostic_admin)):
    await reserve_check(current_user.id)
    return await provider_probe("metrica")


@router.get(
    "/lead/test-utm",
    summary="Тест UTM валидации",
    description="Проверяет UTM-метки на подозрительность"
)
async def test_utm(
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None,
    utm_content: str = None,
    geo_country: str = None,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Тестовый эндпоинт для проверки UTM валидации.
    
    Примеры:
    - ?utm_source=yandex&geo_country=UA → подозрительно (yandex + не Россия)
    - ?utm_content=spam_site_123 → отклонено если в чёрном списке
    """
    from lead_validator.services.utm_validator import utm_validator, UTMData
    
    utm_data = UTMData(
        source=utm_source,
        medium=utm_medium,
        campaign=utm_campaign,
        content=utm_content
    )
    
    result = await utm_validator.validate(utm_data, geo_country=geo_country)
    
    return {
        "is_valid": result.is_valid,
        "reason": result.reason,
        "warning": result.warning,
        "risk_score": result.risk_score,
        "utm_data": {
            "source": utm_source,
            "medium": utm_medium,
            "campaign": utm_campaign,
            "content": utm_content
        },
        "geo_country": geo_country
    }


@router.get(
    "/lead/check-phone",
    summary="Ручная проверка телефона",
    description="""
    Проверяет телефон через DaData без создания лида.
    
    Возвращает:
    - Тип телефона (мобильный/стационарный)
    - Оператор связи
    - Регион
    - Код качества (qc)
    """
)
async def check_phone_manual(
    phone: str = Query(..., min_length=10, max_length=32),
    current_user=Depends(diagnostic_user)
):
    """
    Ручная проверка телефона через DaData.
    Не создаёт лид, только возвращает информацию.
    """
    from lead_validator.services.dadata import dadata_service
    
    await reserve_check(current_user.id)
    
    # Нормализуем телефон
    import re
    cleaned_phone = re.sub(r"[^\d+]", "", phone)
    if not 10 <= len("".join(filter(str.isdigit, cleaned_phone))) <= 15:
        raise HTTPException(status_code=422, detail="Некорректный формат телефона")
    
    # Проверяем через DaData
    dadata_result = await dadata_service.validate_phone(cleaned_phone)
    
    if dadata_result is None:
        return {
            "success": False,
            "error": "DaData unavailable",
            "phone": cleaned_phone
        }
    
    # Проверяем валидность
    is_valid = dadata_service.is_phone_valid(dadata_result)
    
    return {
        "success": True,
        "phone": cleaned_phone,
        "is_valid": is_valid,
        "type": dadata_result.type,
        "provider": dadata_result.provider,
        "region": dadata_result.region,
        "city": dadata_result.city,
        "country": dadata_result.country,
        "timezone": dadata_result.timezone,
        "qc": dadata_result.qc,
        "qc_description": {
            0: "Телефон распознан уверенно",
            1: "Телефон распознан с допущениями",
            2: "Телефон не распознан"
        }.get(dadata_result.qc, "Неизвестно")
    }


@router.post(
    "/lead/test-validate",
    summary="Тестовая валидация лида (без CAPTCHA)",
    description="""
    Тестовый эндпоинт для проверки лида БЕЗ требования CAPTCHA.
    
    Полезно для:
    - Отладки интеграций
    - Тестирования формы
    - Проверки перед деплоем
    
    Ограниченный dry-run: без сохранения, экспорта и уведомлений.
    """
)
async def test_validate_lead(
    phone: str = Query(..., min_length=10, max_length=32),
    email: Optional[str] = Query(None, max_length=254),
    name: Optional[str] = Query(None, max_length=200),
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None,
    project_id: Optional[uuid.UUID] = None,
    request: Request = None,
    current_user=Depends(diagnostic_user),
    db: Session = Depends(get_db)
):
    """
    Тестовая валидация без CAPTCHA.
    Пропускает проверку SmartCaptcha для отладки.
    """
    from lead_validator.services.dadata import dadata_service
    from lead_validator.services.social_checker import social_checker
    
    # Resolve scope before any provider/Redis call, then detach settings from SQL.
    project = None
    if project_id:
        from types import SimpleNamespace
        row = db.query(models.PhoneProject).filter(
            models.PhoneProject.id == project_id,
            models.PhoneProject.owner_id == current_user.id,
            models.PhoneProject.is_active.is_(True),
            sa.or_(models.PhoneProject.client_id.is_(None), sa.exists(sa.select(models.Client.id).where(
                models.Client.id == models.PhoneProject.client_id,
                models.Client.owner_id == current_user.id,
                models.Client.status == models.ClientStatus.ACTIVE))),
        ).first()
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Проект не найден")
        project = SimpleNamespace(
            enable_spam_check=row.enable_spam_check,
            enable_social_check=row.enable_social_check,
        )
    db.rollback()
    await reserve_check(current_user.id)
    
    result = {
        "phone": phone,
        "email": email,
        "name": name,
        "checks": {}
    }
    
    # Нормализуем телефон
    import re
    cleaned_phone = re.sub(r"[^\d+]", "", phone)
    
    # 1. Проверка формата телефона
    digits = "".join(filter(str.isdigit, cleaned_phone))
    if len(digits) < 10:
        result["checks"]["phone_format"] = {"passed": False, "reason": "too_few_digits"}
    elif len(digits) > 15:
        result["checks"]["phone_format"] = {"passed": False, "reason": "too_many_digits"}
    else:
        result["checks"]["phone_format"] = {"passed": True}

    if not result["checks"]["phone_format"]["passed"]:
        result["overall_valid"] = False
        return result
    
    # Dry-run does not expose the shared legacy phone deduplication cache.
    result["checks"]["duplicate"] = {"passed": True, "skipped": True,
        "reason": "dry_run_no_deduplication"}

    # 3. Проверка через DaData
    dadata_result = await dadata_service.validate_phone(cleaned_phone)
    if dadata_result:
        is_valid = dadata_service.is_phone_valid(dadata_result)
        result["checks"]["dadata"] = {
            "passed": is_valid,
            "type": dadata_result.type,
            "provider": dadata_result.provider,
            "region": dadata_result.region,
            "qc": dadata_result.qc
        }
    else:
        result["checks"]["dadata"] = {"passed": False, "error": "unavailable"}
    
    # 4. Проверка email (если есть)
    if email:
        from lead_validator.services.data_quality import data_quality_validator
        email_check = data_quality_validator.validate_email_domain(email)
        result["checks"]["email"] = {
            "passed": email_check.is_valid,
            "reason": email_check.rejection_reason
        }
    
    # Only explicitly enabled project checks; the global CRM is not tenant-owned.
    if project and project.enable_spam_check:
        from lead_validator.services.spam_checker import spam_checker
        spam_result = await spam_checker.check_phone(cleaned_phone)
        result["checks"]["spam"] = {
            "passed": not spam_result.is_spam,
            "is_spam": spam_result.is_spam,
            "category": spam_result.category,
        }

    # 6. Проверка соцсетей (включая InfoTrackPeople как приоритетного провайдера)
    social_enabled_for_test = False
    if project:
        # Без проекта нет разрешения на дополнительное обогащение.
        social_enabled_for_test = bool(getattr(project, "enable_social_check", False))

    if social_enabled_for_test:
        try:
            social_result = await social_checker.check_phone(cleaned_phone, name, email)
            social_error = getattr(social_result, "error", None)
            social_checked = getattr(social_result, "checked", False)
            # Для тест-эндпоинта не считаем кейс "профили не найдены" фатальной ошибкой.
            social_passed = bool(social_checked) or social_error == "No social profiles found"
            result["checks"]["social"] = {
                "passed": social_passed,
                "checked": social_checked,
                "provider": getattr(social_result, "provider", None),
                "has_telegram": getattr(social_result, "has_telegram", None),
                "has_whatsapp": getattr(social_result, "has_whatsapp", None),
                "has_vk": getattr(social_result, "has_vk", None),
                "has_viber": getattr(social_result, "has_viber", None),
                "has_tiktok": getattr(social_result, "has_tiktok", None),
                "telegram_username": getattr(social_result, "telegram_username", None),
                "vk_profile_url": getattr(social_result, "vk_profile_url", None),
                "vk_user_id": getattr(social_result, "vk_user_id", None),
                "error": "provider_unavailable" if social_error and not social_passed else None,
            }
        except Exception:
            logger.warning("Diagnostic social provider failed")
            result["checks"]["social"] = {"passed": False, "error": "provider_unavailable"}
    else:
        result["checks"]["social"] = {
            "passed": True,
            "checked": False,
            "skipped": True,
            "reason": "enable_social_check=false for project",
        }
    
    # Итоговый результат
    all_passed = all(
        check.get("passed", True) 
        for check in result["checks"].values()
    )
    result["overall_valid"] = all_passed
    
    # Diagnostics never persist a lead, mark duplicates or send customer notifications.
    return result


def _get_client_ip(request: Request) -> str:
    """
    Получить реальный IP клиента.
    
    Учитывает заголовки от прокси/балансировщика:
    - X-Forwarded-For
    - X-Real-IP
    - CF-Connecting-IP (Cloudflare)
    """
    # Cloudflare
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    
    # X-Forwarded-For (может быть список через запятую)
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # Берём первый IP из списка (оригинальный клиент)
        return xff.split(",")[0].strip()
    
    # X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback на IP из соединения
    if request.client:
        return request.client.host
    
    return "unknown"


@router.get(
    "/reports/quality",
    summary="Отчёт по качеству трафика для подрядчиков",
    description="""
    Генерирует отчёт по качеству трафика за указанный период.
    
    Содержит:
    - Топ-10 худших площадок по коэффициенту мусора
    - Распределение причин отклонения
    - Динамику качества трафика по неделям
    - Список площадок в чёрном списке
    
    Форматы: JSON (по умолчанию) или Excel (format=excel)
    """
)
def get_quality_report(
    days: int = Query(7, ge=1, le=365),
    format: Literal['json', 'excel'] = "json",
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Генерация отчёта по качеству трафика.
    
    Args:
        days: Период анализа в днях (по умолчанию 7)
        format: Формат отчёта (json или excel)
    """
    try:
        from lead_validator.services.quality_report import snapshot, render_xlsx
        report, blacklist = snapshot(db, current_user.id, days)
        
        # Формируем данные отчёта
        report_data = {
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
                "days": days,
                "timezone": "UTC"
            },
            "overall": {
                "total_leads": report.total_leads,
                "total_rejected": report.total_rejected,
                "rejection_rate": round(report.overall_rejection_rate, 2)
            },
            "top_bad_sources": [
                {
                    "project_id": s.project_id,
                    "project_name": s.project_name,
                    "source": s.source,
                    "campaign": s.campaign,
                    "content": s.content,
                    "total_leads": s.total_leads,
                    "rejected_leads": s.rejected_leads,
                    "rejection_rate": round(s.rejection_rate, 2),
                    "rejection_reasons": s.rejection_reasons
                }
                for s in report.bad_sources[:10]
            ],
            "rejection_reasons": report.top_rejection_reasons,
            "other_rejection_count": report.other_rejection_count,
            "source": "persisted_project_leads",
            "blacklisted_placements": blacklist,
            "generated_at": report.period_end.isoformat()
        }
        
        if format.lower() == "excel":
            filename = f"quality_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            return Response(
                content=render_xlsx(report, blacklist),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # JSON формат
            return JSONResponse(content=report_data)
            
    except Exception as e:
        from lead_validator.services.scoped_stats import StatsLimitExceeded
        if isinstance(e, StatsLimitExceeded):
            raise HTTPException(status_code=422, detail=str(e)) from e
        logger.error("Error generating scoped quality report: %s", type(e).__name__)
        return JSONResponse(
            status_code=500,
            content={"error": "Не удалось подготовить отчёт качества"}
        )


@router.get(
    "/reports/blacklist",
    summary="Список площадок в чёрном списке",
    description="Возвращает список всех площадок в динамическом чёрном списке"
)
def get_blacklist(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Получить список площадок в чёрном списке."""
    try:
        from lead_validator.services.scoped_placements import get_blacklist as scoped_blacklist
        blacklist = scoped_blacklist(db, current_user.id)
        return {
            "count": len(blacklist),
            "placements": blacklist
        }
    except Exception as e:
        from lead_validator.services.scoped_stats import StatsLimitExceeded
        if isinstance(e, StatsLimitExceeded):
            raise HTTPException(status_code=422, detail=str(e)) from e
        logger.error("Error getting scoped blacklist: %s", type(e).__name__)
        return JSONResponse(
            status_code=500,
            content={"error": "Не удалось загрузить чёрный список"}
        )
