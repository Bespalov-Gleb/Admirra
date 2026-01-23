"""
Цепочка валидаторов для проверки входящих лидов.
Проверки идут от дешёвых к дорогим для оптимизации.
"""

import logging
import time
from typing import Optional, Tuple
from lead_validator.config import settings
from lead_validator.schemas import LeadInput, ValidationResult, RejectedLead
from lead_validator.services.dadata import dadata_service, DaDataPhoneResponse
from lead_validator.services.redis_service import redis_service
from lead_validator.services.trash_logger import trash_logger
from lead_validator.services.telegram import telegram_notifier
from lead_validator.services.captcha import captcha_validator
from lead_validator.services.utm_validator import utm_validator, UTMData
from lead_validator.services.metrica_service import metrica_service
from lead_validator.services.request_validator import request_validator
from lead_validator.services.data_quality import data_quality_validator
from lead_validator.services.analytics import analytics_service
from lead_validator.services.email_mx_validator import email_mx_validator, timezone_validator

logger = logging.getLogger("lead_validator.validators")


class LeadValidator:
    """
    Многоуровневая валидация лидов.
    
    Порядок проверок (от дешёвых к дорогим):
    0. CAPTCHA: Yandex SmartCaptcha
    0.5. HTTP заголовки: User-Agent, Referer
    1. Антибот: timestamp, honeypot
    2. Качество данных: пустые поля, формат телефона, email, имя
    3. Rate Limiting: проверка IP (Redis)
    4. Дедупликация: хеш телефона (Redis)
    5. DaData: валидация телефона (внешний API)
    6. UTM валидация: подозрительные метки, GeoIP, чёрный список
    """
    
    async def validate(
        self, 
        lead: LeadInput,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
    ) -> ValidationResult:
        """
        Главный метод валидации лида.
        
        Args:
            lead: Входные данные лида
            client_ip: IP адрес клиента для rate limiting
            
        Returns:
            ValidationResult с результатом проверки
        """
        start_time = time.time()
        
        # Сохраняем IP в lead для логирования
        if client_ip:
            lead.client_ip = client_ip
        
        # === Уровень 0: CAPTCHA (Yandex SmartCaptcha) ===
        captcha_passed, captcha_error = await captcha_validator.validate(
            lead.smart_token or "", 
            client_ip
        )
        if not captcha_passed:
            return await self._reject(lead, f"captcha_failed: {captcha_error}", start_time)
        
        # === Уровень 0.5: HTTP заголовки (User-Agent, Referer) ===
        if user_agent is not None:
            request_check = request_validator.validate(user_agent, referer)
            if not request_check.is_valid:
                return await self._reject(lead, request_check.rejection_reason or "request_invalid", start_time)
        
        # === Уровень 1: Антибот ===
        rejection = await self._check_antibot(lead)
        if rejection:
            return await self._reject(lead, rejection, start_time)
        
        # === Уровень 2: Качество данных ===
        rejection = self._check_data_quality(lead)
        if rejection:
            return await self._reject(lead, rejection, start_time)
        
        # === Уровень 3: Rate Limiting ===
        if client_ip:
            allowed = await redis_service.check_rate_limit(client_ip)
            if not allowed:
                return await self._reject(
                    lead, 
                    "rate_limit_exceeded", 
                    start_time
                )
        
        # === Уровень 4: Дедупликация телефона ===
        is_duplicate = await redis_service.is_duplicate(lead.phone)
        if is_duplicate:
            return await self._reject(lead, "duplicate_phone", start_time)
        
        # === Уровень 4.5: Дедупликация email ===
        if lead.email:
            is_email_dup = await redis_service.is_email_duplicate(lead.email)
            if is_email_dup:
                return await self._reject(lead, "duplicate_email", start_time)
        
        # === Уровень 4.6: MX-записи email домена ===
        if lead.email and settings.MX_CHECK_ENABLED:
            mx_result = email_mx_validator.check_mx(lead.email)
            if not mx_result.has_mx:
                return await self._reject(
                    lead, 
                    f"email_no_mx:{mx_result.error or 'no_records'}", 
                    start_time
                )
        
        # === Уровень 4.7: Проверка timezone браузера ===
        if lead.browser_timezone and lead.geo_country:
            tz_result = timezone_validator.validate(
                lead.browser_timezone,
                ip_country=lead.geo_country
            )
            if tz_result.is_suspicious:
                logger.warning(f"Suspicious timezone for {lead.phone}: {tz_result.warning}")
                # Не отклоняем, только логируем (можно изменить на _reject если нужно)
        
        # === Уровень 5: DaData валидация ===
        dadata_result = await dadata_service.validate_phone(lead.phone)
        
        if dadata_result is None:
            # DaData недоступен
            if settings.FAIL_OPEN_MODE:
                logger.warning(f"DaData unavailable, fail-open for: {lead.phone}")
                # Пропускаем но помечаем
                return await self._accept(
                    lead, 
                    dadata_result, 
                    start_time,
                    note="dadata_unavailable"
                )
            else:
                return await self._reject(
                    lead, 
                    "dadata_unavailable", 
                    start_time
                )
        
        if not dadata_service.is_phone_valid(dadata_result):
            return await self._reject(
                lead, 
                f"invalid_phone_qc_{dadata_result.qc}",
                start_time,
                dadata=dadata_result
            )
        
        # === Уровень 5.5: DaData валидация EMAIL ===
        if lead.email and settings.DADATA_API_KEY:
            email_result = await dadata_service.validate_email(lead.email)
            
            if email_result:
                # Проверяем qc-код
                if not dadata_service.is_email_valid(email_result):
                    return await self._reject(
                        lead,
                        f"invalid_email_qc_{email_result.get('qc')}",
                        start_time,
                        dadata=dadata_result
                    )
                
                # Проверяем на одноразовый email
                if dadata_service.is_email_disposable(email_result):
                    return await self._reject(
                        lead,
                        "email_disposable",
                        start_time,
                        dadata=dadata_result
                    )
                
                # Логируем тип email
                email_type = dadata_service.get_email_type(email_result)
                logger.info(f"Email type for {lead.phone}: {email_type}")
        
        # === Уровень 6: UTM валидация ===
        if settings.UTM_VALIDATION_ENABLED:
            utm_data = UTMData(
                source=lead.utm_source,
                medium=lead.utm_medium,
                campaign=lead.utm_campaign,
                content=lead.utm_content,
                term=lead.utm_term
            )
            utm_result = utm_validator.validate(
                utm_data, 
                client_ip=client_ip,
                geo_country=lead.geo_country
            )
            if not utm_result.is_valid:
                return await self._reject(
                    lead, 
                    f"utm_invalid:{utm_result.reason}",
                    start_time,
                    dadata=dadata_result
                )
            if utm_result.warning:
                logger.warning(f"UTM warning for {lead.phone}: {utm_result.warning}")
        
        # === ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ ===
        return await self._accept(lead, dadata_result, start_time)
    
    async def _check_antibot(self, lead: LeadInput) -> Optional[str]:
        """
        Проверка антибот-полей.
        
        Returns:
            Причина отклонения или None если OK
        """
        # Honeypot должен быть пустым
        if lead.honeypot:
            logger.info(f"Honeypot triggered: {lead.phone}")
            return "honeypot_filled"
        
        # Проверка timestamp
        if lead.timestamp is not None:
            current_time = int(time.time())
            fill_time = current_time - lead.timestamp
            
            # Слишком быстро — бот
            if fill_time < settings.MIN_FORM_FILL_TIME_SEC:
                logger.info(f"Too fast form fill: {fill_time}s for {lead.phone}")
                return "form_filled_too_fast"
            
            # Слишком долго — подозрительно (или timestamp старый)
            if fill_time > settings.MAX_FORM_FILL_TIME_SEC:
                logger.info(f"Stale timestamp: {fill_time}s for {lead.phone}")
                return "stale_timestamp"
        
        return None
    
    def _check_data_quality(self, lead: LeadInput) -> Optional[str]:
        """
        Базовая проверка качества данных.
        
        Returns:
            Причина отклонения или None если OK
        """
        # Телефон обязателен и не должен быть пустым
        if not lead.phone or len(lead.phone.strip()) < 5:
            return "empty_or_short_phone"
        
        # Телефон должен содержать хотя бы 10 цифр
        digits = "".join(filter(str.isdigit, lead.phone))
        if len(digits) < 10:
            return "phone_too_few_digits"
        
        if len(digits) > 15:
            return "phone_too_many_digits"
        
        # === Проверка email на одноразовый домен ===
        if lead.email:
            email_check = data_quality_validator.validate_email_domain(lead.email)
            if not email_check.is_valid:
                return email_check.rejection_reason
        
        # === Проверка имени на стоп-лист ===
        if lead.name:
            name_check = data_quality_validator.validate_name(lead.name)
            if not name_check.is_valid:
                return name_check.rejection_reason
        
        return None
    
    async def _reject(
        self, 
        lead: LeadInput, 
        reason: str, 
        start_time: float,
        dadata: Optional[DaDataPhoneResponse] = None
    ) -> ValidationResult:
        """
        Отклонить лид и залогировать.
        """
        execution_time = (time.time() - start_time) * 1000
        
        logger.info(f"Lead rejected: {lead.phone} - {reason}")
        
        # Записываем в аналитику
        analytics_service.record_lead(
            utm_source=lead.utm_source,
            utm_campaign=lead.utm_campaign,
            utm_content=lead.utm_content,
            rejected=True,
            rejection_reason=reason
        )
        
        # Логируем в Airtable/файл (async, не блокируем ответ)
        rejected = RejectedLead(
            phone=lead.phone,
            email=lead.email,
            name=lead.name,
            rejection_reason=reason,
            utm_source=lead.utm_source,
            utm_medium=lead.utm_medium,
            utm_campaign=lead.utm_campaign,
            client_ip=lead.client_ip,
            dadata_qc=dadata.qc if dadata else None,
            phone_type=dadata.type if dadata else None
        )
        
        # Не ждём завершения логирования
        try:
            await trash_logger.log_rejected(rejected)
        except Exception as e:
            logger.error(f"Failed to log rejected lead: {e}")
        
        return ValidationResult(
            success=False,
            rejection_reason=reason,
            execution_time_ms=round(execution_time, 2),
            dadata_qc=dadata.qc if dadata else None,
            phone_type=dadata.type if dadata else None
        )
    
    async def _accept(
        self, 
        lead: LeadInput, 
        dadata: Optional[DaDataPhoneResponse],
        start_time: float,
        note: Optional[str] = None
    ) -> ValidationResult:
        """
        Принять лид, отправить в Telegram, сохранить хеш.
        """
        execution_time = (time.time() - start_time) * 1000
        
        logger.info(f"Lead accepted: {lead.phone}")
        
        # Записываем в аналитику (принятый лид)
        analytics_service.record_lead(
            utm_source=lead.utm_source,
            utm_campaign=lead.utm_campaign,
            utm_content=lead.utm_content,
            rejected=False
        )
        
        # Сохраняем хеш телефона для дедупликации
        await redis_service.mark_phone(lead.phone)
        
        # Сохраняем хеш email для дедупликации
        if lead.email:
            await redis_service.mark_email(lead.email)
        
        # Отправляем уведомление в Telegram
        try:
            await telegram_notifier.send_new_lead(
                lead,
                phone_type=dadata.type if dadata else None,
                provider=dadata.provider if dadata else None,
                region=dadata.region if dadata else None
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
        
        # Отправляем конверсию в Яндекс.Метрику
        try:
            # Используем ym_uid если есть, иначе IP как fallback
            client_id = lead.ym_uid or lead.client_ip or "unknown"
            await metrica_service.send_quality_lead(client_id)
        except Exception as e:
            logger.error(f"Failed to send Metrica conversion: {e}")
        
        return ValidationResult(
            success=True,
            lead_id=f"lead_{int(time.time())}",  # Простой ID
            execution_time_ms=round(execution_time, 2),
            phone_type=dadata.type if dadata else None,
            phone_provider=dadata.provider if dadata else None,
            phone_region=dadata.region if dadata else None,
            dadata_qc=dadata.qc if dadata else None
        )


# Глобальный экземпляр
lead_validator = LeadValidator()

