"""
FastAPI роутер для приёма лидов.
Основной эндпоинт: POST /api/lead/
"""

import logging
from fastapi import APIRouter, Request, BackgroundTasks, Depends
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
from typing import Optional

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
    background_tasks: BackgroundTasks
) -> ValidationResult:
    """
    Основной эндпоинт валидации лида.
    
    Принимает JSON с данными формы и возвращает результат валидации.
    Время обработки включено в ответ для мониторинга латентности.
    """
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
async def get_stats(
    date: str = None,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Получить статистику отклонённых заявок.
    
    Args:
        date: Дата в формате YYYY-MM-DD (по умолчанию сегодня)
    """
    stats = await trash_logger.get_stats(date)
    return stats


@router.get(
    "/lead/test-telegram",
    summary="Тест Telegram уведомлений",
    description="Проверяет соединение с Telegram и отправляет тестовое сообщение"
)
async def test_telegram(
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Тестовый эндпоинт для отладки Telegram.
    Проверяет настройки бота и отправляет тестовое сообщение.
    """
    result = await telegram_notifier.test_connection()
    return result


@router.get(
    "/lead/test-captcha-api",
    summary="Тест Yandex SmartCaptcha API",
    description="Проверяет подключение к Yandex Cloud и возвращает список капч"
)
async def test_captcha_api(
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Тестовый эндпоинт для проверки Yandex Cloud SmartCaptcha API.
    Использует IAM токен и folder_id из .env для получения списка капч.
    """
    import httpx
    import os
    from dotenv import load_dotenv
    
    # Перезагружаем .env для получения актуальных значений
    load_dotenv(override=True)
    
    iam_token = os.getenv("YANDEX_IAM_TOKEN")
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    
    if not iam_token:
        return {"error": True, "message": "YANDEX_IAM_TOKEN not set in .env"}
    if not folder_id:
        return {"error": True, "message": "YANDEX_FOLDER_ID not set in .env"}
    
    # Debug info
    token_preview = f"{iam_token[:30]}...{iam_token[-20:]}" if len(iam_token) > 50 else iam_token
    
    url = f"https://smartcaptcha.api.cloud.yandex.net/smartcaptcha/v1/captchas?folderId={folder_id}"
    headers = {"Authorization": f"Bearer {iam_token}"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            data = response.json()
            
            if response.status_code == 200:
                # API возвращает "resources", не "captchas"
                captchas = data.get("resources", [])
                return {
                    "success": True,
                    "folder_id": folder_id,
                    "token_preview": token_preview,
                    "captchas_count": len(captchas),
                    "captchas": [
                        {"id": c.get("id"), "name": c.get("name"), "complexity": c.get("complexity"), "clientKey": c.get("clientKey")}
                        for c in captchas
                    ]
                }
            else:
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "folder_id": folder_id,
                    "token_preview": token_preview,
                    "details": data
                }
    except Exception as e:
        return {"error": True, "message": str(e), "token_preview": token_preview}


@router.get(
    "/lead/test-metrica",
    summary="Тест Яндекс.Метрика API",
    description="Проверяет подключение к Яндекс.Метрике и возвращает информацию о счётчике"
)
async def test_metrica(
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Тестовый эндпоинт для проверки Яндекс.Метрика API.
    Возвращает информацию о счётчике если настроено.
    """
    from lead_validator.services.metrica_service import metrica_service
    return await metrica_service.test_connection()


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
    phone: str,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Ручная проверка телефона через DaData.
    Не создаёт лид, только возвращает информацию.
    """
    from lead_validator.services.dadata import dadata_service
    
    logger.info(f"Manual phone check: {phone}")
    
    # Нормализуем телефон
    import re
    cleaned_phone = re.sub(r"[^\d+]", "", phone)
    
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
    
    НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ!
    """
)
async def test_validate_lead(
    phone: str,
    email: str = None,
    name: str = None,
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None,
    request: Request = None,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Тестовая валидация без CAPTCHA.
    Пропускает проверку SmartCaptcha для отладки.
    """
    from lead_validator.services.dadata import dadata_service
    from lead_validator.services.redis_service import redis_service
    
    logger.info(f"Test validation: phone={phone}")
    
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
    
    # 2. Проверка дедупликации
    is_duplicate = await redis_service.is_duplicate(cleaned_phone)
    result["checks"]["duplicate"] = {"passed": not is_duplicate, "is_duplicate": is_duplicate}
    
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
    
    # Итоговый результат
    all_passed = all(
        check.get("passed", True) 
        for check in result["checks"].values()
    )
    result["overall_valid"] = all_passed
    
    # Отправляем уведомление в Telegram (если валидация пройдена)
    if all_passed:
        try:
            from lead_validator.services.telegram import telegram_notifier
            from lead_validator.schemas import LeadInput
            
            # Создаем объект лида для уведомления
            test_lead = LeadInput(
                phone=phone,
                email=email or None,
                name=name or None,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign
            )
            
            dadata_info = result["checks"].get("dadata", {})
            
            await telegram_notifier.send_new_lead(
                lead=test_lead,
                phone_type=dadata_info.get("type"),
                provider=dadata_info.get("provider"),
                region=dadata_info.get("region"),
                is_test=True
            )
        except Exception as e:
            logger.error(f"Failed to send test Telegram notification: {e}")
    
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
async def get_quality_report(
    days: int = 7,
    format: str = "json",
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Генерация отчёта по качеству трафика.
    
    Args:
        days: Период анализа в днях (по умолчанию 7)
        format: Формат отчёта (json или excel)
    """
    try:
        # Генерируем отчёт
        report = analytics_service.generate_weekly_report()
        
        # Получаем чёрный список площадок
        blacklist = await placement_blacklist.get_blacklist()
        
        # Формируем данные отчёта
        report_data = {
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
                "days": days
            },
            "overall": {
                "total_leads": report.total_leads,
                "total_rejected": report.total_rejected,
                "rejection_rate": round(report.overall_rejection_rate, 2)
            },
            "top_bad_sources": [
                {
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
            "blacklisted_placements": blacklist,
            "generated_at": datetime.now().isoformat()
        }
        
        if format.lower() == "excel":
            # Генерируем Excel файл
            import io
            import pandas as pd
            
            # Создаём Excel с несколькими листами
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Лист 1: Плохие источники
                if report.bad_sources:
                    bad_sources_df = pd.DataFrame([
                        {
                            "Источник": s.source,
                            "Кампания": s.campaign,
                            "Площадка": s.content,
                            "Всего заявок": s.total_leads,
                            "Отклонено": s.rejected_leads,
                            "Процент мусора": round(s.rejection_rate, 2)
                        }
                        for s in report.bad_sources
                    ])
                    bad_sources_df.to_excel(writer, sheet_name="Плохие источники", index=False)
                
                # Лист 2: Причины отклонения
                if report.top_rejection_reasons:
                    reasons_df = pd.DataFrame([
                        {"Причина": reason, "Количество": count}
                        for reason, count in report.top_rejection_reasons.items()
                    ])
                    reasons_df.to_excel(writer, sheet_name="Причины отклонения", index=False)
                
                # Лист 3: Чёрный список
                if blacklist:
                    blacklist_df = pd.DataFrame(blacklist)
                    blacklist_df.to_excel(writer, sheet_name="Чёрный список", index=False)
            
            output.seek(0)
            filename = f"quality_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            return Response(
                content=output.read(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # JSON формат
            return JSONResponse(content=report_data)
            
    except Exception as e:
        logger.error(f"Error generating quality report: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get(
    "/reports/blacklist",
    summary="Список площадок в чёрном списке",
    description="Возвращает список всех площадок в динамическом чёрном списке"
)
async def get_blacklist(
    current_user: models.User = Depends(security.get_current_user)
):
    """Получить список площадок в чёрном списке."""
    try:
        blacklist = await placement_blacklist.get_blacklist()
        return {
            "count": len(blacklist),
            "placements": blacklist
        }
    except Exception as e:
        logger.error(f"Error getting blacklist: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

