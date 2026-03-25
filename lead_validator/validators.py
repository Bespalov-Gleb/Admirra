"""
Цепочка валидаторов для проверки входящих лидов.
Проверки идут от дешёвых к дорогим для оптимизации.
"""

import logging
import time
import json
import uuid
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session
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
from lead_validator.services.social_checker import social_checker
from lead_validator.services.social_merge import merge_social_accounts_payload, social_payload_to_json
from lead_validator.services.lead_scoring import compute_lead_score
from lead_validator.services.gosuslugi_checker import gosuslugi_checker
from lead_validator.services.spam_checker import spam_checker, SpamCheckResult
from lead_validator.services.bitrix_service import bitrix_service, BitrixDuplicateResult
from core import models, security

logger = logging.getLogger("lead_validator.validators")


def _merge_bool_from_form(api_val: Optional[bool], override_from_form: Optional[bool]) -> Optional[bool]:
    """Если в форме явно указан мессенджер — считаем has_* True."""
    if override_from_form is True:
        return True
    return api_val


def _restore_name_from_itp_fio(
    current_name: Optional[str],
    current_surname: Optional[str],
    itp_name: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Восстанавливает имя/фамилию из полного ФИО ITP, не перетирая корректно заполненные поля.
    Пример: "Иванов Иван Иванович" + name="Иван" -> surname="Иванов".
    """
    fio = re.sub(r"\s+", " ", (itp_name or "").strip())
    if not fio:
        return current_name, current_surname
    parts = fio.split(" ")
    if len(parts) < 2:
        return current_name, current_surname

    name = (current_name or "").strip() or None
    surname = (current_surname or "").strip() or None

    # Базовое предположение для RU-формата: "Фамилия Имя [Отчество]"
    candidate_surname = parts[0]
    candidate_name = parts[1]

    # Если текущее имя уже совпало с первым словом (формат "Имя Фамилия"), подстраиваемся.
    if name:
        n = name.lower()
        if n == parts[0].lower():
            candidate_name = parts[0]
            candidate_surname = parts[1]
        elif n == parts[1].lower():
            candidate_name = parts[1]
            candidate_surname = parts[0]

    if not name:
        name = candidate_name
    if not surname:
        surname = candidate_surname

    return name, surname


def _get_metrica_credentials_from_project(db: Optional[Session], project) -> Tuple[Optional[str], Optional[str]]:
    """
    Получить OAuth-токен и ID счётчика Метрики из интеграции Яндекса клиента проекта.
    Если проект привязан к клиенту и у клиента есть интеграция YANDEX_DIRECT,
    возвращаем (token, counter_id) для отправки офлайн-конверсий; иначе (None, None).
    """
    if not db or not project or not getattr(project, "client_id", None):
        return (None, None)
    try:
        integration = (
            db.query(models.Integration)
            .filter(
                models.Integration.client_id == project.client_id,
                models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            )
            .first()
        )
        if not integration or not integration.access_token:
            return (None, None)
        token = security.decrypt_token(integration.access_token)
        counter_id = None
        if getattr(integration, "selected_counters", None):
            try:
                counters = json.loads(integration.selected_counters)
                if isinstance(counters, list) and counters:
                    counter_id = str(counters[0])
            except (TypeError, ValueError):
                pass
        if not counter_id and getattr(integration, "account_id", None):
            counter_id = str(integration.account_id)
        if not token or not counter_id:
            return (None, None)
        return (token, counter_id)
    except Exception as e:
        logger.debug("Could not get Metrica credentials from integration: %s", e)
        return (None, None)


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
        referer: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        form_data: Optional[dict] = None,
        skip_request_validation: bool = False,
        skip_antibot_validation: bool = False,
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
        
        # Загружаем project для проектных настроек (spam/bitrix gating)
        project = None
        if project_id and db:
            project = db.query(models.PhoneProject).filter_by(id=project_id).first()
        
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
        # Пропускаем для webhook (Marquiz, Tilda) — запрос приходит с серверов, авторизация по X-Webhook-Secret
        if not skip_request_validation and user_agent is not None:
            request_check = request_validator.validate(user_agent, referer)
            if not request_check.is_valid:
                return await self._reject(lead, request_check.rejection_reason or "request_invalid", start_time)
        
        # === Уровень 1: Антибот ===
        if not skip_antibot_validation:
            rejection = await self._check_antibot(lead)
            if rejection:
                return await self._reject(lead, rejection, start_time)
        
        # === Уровень 2: Качество данных ===
        rejection = self._check_data_quality(lead)
        if rejection:
            return await self._reject(lead, rejection, start_time)
        
        # === Уровень 3: Rate Limiting по IP ===
        if client_ip:
            allowed = await redis_service.check_rate_limit(client_ip)
            if not allowed:
                return await self._reject(
                    lead, 
                    "rate_limit_exceeded_ip", 
                    start_time
                )
        
        # === Уровень 3.5: Rate Limiting по телефону ===
        allowed_phone = await redis_service.check_phone_rate_limit(lead.phone)
        if not allowed_phone:
            return await self._reject(
                lead,
                "rate_limit_exceeded_phone",
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
        
        # === Уровень 4.6: Проверка в CRM (Bitrix24) ===
        # Информационная проверка - не отклоняем, но логируем если контакт найден
        run_bitrix = (project is None or getattr(project, "enable_bitrix_check", False)) and bitrix_service.enabled
        if run_bitrix:
            bitrix_duplicate = await bitrix_service.find_duplicates(phone=lead.phone, email=lead.email)
        else:
            bitrix_duplicate = BitrixDuplicateResult()
        if bitrix_duplicate.has_duplicate:
            logger.info(
                f"Found existing Bitrix24 contact {bitrix_duplicate.contact_id} "
                f"by {bitrix_duplicate.duplicate_type} for {lead.phone[:10]}..."
            )
            # Можно создать новое дело для существующего контакта или обновить контакт
            # Это делается в _accept или _export_lead
        
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
                    note="dadata_unavailable",
                    project_id=project_id,
                    db=db,
                    form_data=form_data,
                    user_agent=user_agent,
                    referer=referer
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
        
        # === Уровень 5.5: Проверка на спам-номера ===
        run_spam = project is None or getattr(project, "enable_spam_check", True)
        if run_spam:
            spam_result = await spam_checker.check_phone(lead.phone)
        else:
            spam_result = SpamCheckResult()
        if spam_result.is_spam:
            return await self._reject(
                lead,
                f"spam_phone:{spam_result.category or 'unknown'}",
                start_time,
                dadata=dadata_result
            )
        # Если номер в белом списке - логируем, но не отклоняем
        if spam_result.is_whitelisted:
            logger.info(f"Phone {lead.phone[:10]}... is whitelisted, skipping spam check")
        
        # === Уровень 6: UTM валидация ===
        if settings.UTM_VALIDATION_ENABLED:
            utm_data = UTMData(
                source=lead.utm_source,
                medium=lead.utm_medium,
                campaign=lead.utm_campaign,
                content=lead.utm_content,
                term=lead.utm_term
            )
            
            # project уже загружен в начале validate()
            utm_result = await utm_validator.validate(
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
        return await self._accept(
            lead, 
            dadata_result, 
            start_time,
            project_id=project_id,
            db=db,
            form_data=form_data,
            user_agent=user_agent,
            referer=referer
        )
    
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
        
        # Проверка JavaScript-токена
        if settings.JS_TOKEN_ENABLED:
            if not lead.js_token or len(lead.js_token.strip()) < 10:
                logger.info(f"Missing or invalid JS token for {lead.phone}")
                return "js_token_missing_or_invalid"
        
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
        dadata: Optional[DaDataPhoneResponse] = None,
        project_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        form_data: Optional[dict] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
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
        
        # Сохраняем заявку в базу (со статусом SPAM или INVALID)
        if project_id and db:
            try:
                from core import models
                lead_record = models.Lead(
                    project_id=project_id,
                    phone=lead.phone,
                    email=lead.email,
                    name=lead.name,
                    utm_source=lead.utm_source,
                    utm_medium=lead.utm_medium,
                    utm_campaign=lead.utm_campaign,
                    utm_content=lead.utm_content,
                    utm_term=lead.utm_term,
                    client_ip=lead.client_ip,
                    user_agent=user_agent,
                    referer=referer,
                    geo_country=lead.geo_country,
                    browser_timezone=lead.browser_timezone,
                    ym_uid=lead.ym_uid,
                    form_data=json.dumps(form_data) if form_data else None,
                    is_valid=False,
                    validation_reason=reason,
                    phone_type=dadata.type if dadata else None,
                    phone_provider=dadata.provider if dadata else None,
                    phone_region=dadata.region if dadata else None,
                    phone_city=dadata.city if dadata else None,
                    dadata_qc=dadata.qc if dadata else None,
                    status=models.LeadStatus.SPAM if "spam" in reason.lower() else models.LeadStatus.INVALID,
                    is_spam="spam" in reason.lower()
                )
                db.add(lead_record)
                db.commit()
                logger.info(f"Rejected lead saved to database: {lead_record.id}")
                
                # Выгружаем в CRM/почту/телеграм если нужно
                project = db.query(models.PhoneProject).filter_by(id=project_id).first()
                if project:
                    await self._export_lead(lead_record, project, db)
            except Exception as e:
                logger.error(f"Failed to save rejected lead to database: {e}")
                if db:
                    db.rollback()
        
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
        note: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        form_data: Optional[dict] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
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
        
        # Загружаем проект заранее (для имени, social_check, source)
        project = None
        if project_id and db:
            from core import models
            project = db.query(models.PhoneProject).filter_by(id=project_id).first()
        
        # Social check до Telegram, чтобы показать мессенджеры в уведомлении
        social_result = None
        if project and getattr(project, "enable_social_check", False):
            try:
                social_result = await social_checker.check_phone(lead.phone, lead.name, lead.email)
                if social_result and not getattr(social_result, "checked", False):
                    logger.info(
                        "Social check incomplete for %s: %s",
                        lead.phone,
                        getattr(social_result, "error", None) or "no provider",
                    )
            except Exception as e:
                logger.warning(f"Social check failed before telegram: {e}")
        
        # Определяем источник (Marquiz, Tilda, ручной ввод)
        source = None
        if form_data:
            source = form_data.get("source") or form_data.get("_source")
        if not source and referer:
            if "marquiz" in referer.lower():
                source = "Marquiz"
            elif "tilda" in referer.lower():
                source = "Tilda"
        
        # Отправляем уведомление в Telegram (с полными данными)
        try:
            await telegram_notifier.send_new_lead(
                lead,
                phone_type=dadata.type if dadata else None,
                provider=dadata.provider if dadata else None,
                region=dadata.region if dadata else None,
                city=dadata.city if dadata else None,
                social_result=social_result,
                project_name=project.name if project else None,
                source=source,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
        
        # === СТАДИЯ 2: Сохранение в БД и выгрузка ===
        
        # Сохраняем заявку в базу данных
        lead_record = None
        if project_id and db:
            try:
                # Создаём запись заявки
                lead_record = models.Lead(
                    project_id=project_id,
                    phone=lead.phone,
                    email=lead.email,
                    name=lead.name,
                    utm_source=lead.utm_source,
                    utm_medium=lead.utm_medium,
                    utm_campaign=lead.utm_campaign,
                    utm_content=lead.utm_content,
                    utm_term=lead.utm_term,
                    client_ip=lead.client_ip,
                    user_agent=user_agent,
                    referer=referer,
                    geo_country=lead.geo_country,
                    browser_timezone=lead.browser_timezone,
                    ym_uid=lead.ym_uid,
                    form_data=json.dumps(form_data) if form_data else None,
                    is_valid=True,
                    validation_reason="passed_all_checks",
                    phone_type=dadata.type if dadata else None,
                    phone_provider=dadata.provider if dadata else None,
                    phone_region=dadata.region if dadata else None,
                    phone_city=dadata.city if dadata else None,
                    dadata_qc=dadata.qc if dadata else None,
                    status=models.LeadStatus.VALID
                )
                
                # Соцсети: API (если включено) + данные формы (telegram/vk/...) в social_accounts_data
                sr = social_result if (project and project.enable_social_check) else None
                merged_social, form_overrides = merge_social_accounts_payload(sr, form_data)
                social_json = social_payload_to_json(merged_social)
                if social_json:
                    lead_record.social_accounts_data = social_json

                # Если ITP нашёл email — заполняем поле лида (в UI выводится именно из lead.email)
                if sr and getattr(sr, "itp_email", None) and not lead_record.email:
                    lead_record.email = sr.itp_email

                # Если ITP вернул ФИО, а в заявке только имя/неполные поля — восстанавливаем name/surname.
                if sr and getattr(sr, "itp_name", None):
                    lead_record.name, lead_record.surname = _restore_name_from_itp_fio(
                        lead_record.name,
                        lead_record.surname,
                        sr.itp_name,
                    )

                lead_record.has_telegram = _merge_bool_from_form(
                    sr.has_telegram if sr else None,
                    form_overrides.get("has_telegram"),
                )
                lead_record.has_whatsapp = _merge_bool_from_form(
                    sr.has_whatsapp if sr else None,
                    form_overrides.get("has_whatsapp"),
                )
                lead_record.has_viber = _merge_bool_from_form(
                    sr.has_viber if sr else None,
                    form_overrides.get("has_viber"),
                )
                lead_record.has_tiktok = _merge_bool_from_form(
                    sr.has_tiktok if sr else None,
                    form_overrides.get("has_tiktok"),
                )
                lead_record.has_vk = _merge_bool_from_form(
                    sr.has_vk if sr else None,
                    form_overrides.get("has_vk"),
                )

                # Если включена проверка Госуслуг
                if project and project.enable_gosuslugi_check:
                    gosuslugi_result = await gosuslugi_checker.check(lead.phone)
                    lead_record.has_gosuslugi = gosuslugi_result.has_registration
                    if gosuslugi_result.has_registration:
                        lead_record.gosuslugi_name = gosuslugi_result.name
                        lead_record.gosuslugi_surname = gosuslugi_result.surname
                        # Заполняем имя/фамилию если нет
                        if not lead_record.name and gosuslugi_result.name:
                            lead_record.name = gosuslugi_result.name
                        if not lead_record.surname and gosuslugi_result.surname:
                            lead_record.surname = gosuslugi_result.surname

                # Скоринг квалификации (отдельный флаг проекта)
                if project and getattr(project, "enable_lead_scoring", False):
                    score_res = compute_lead_score(
                        dadata=dadata,
                        has_telegram=lead_record.has_telegram,
                        has_whatsapp=lead_record.has_whatsapp,
                        has_vk=lead_record.has_vk,
                        has_viber=lead_record.has_viber,
                        has_tiktok=lead_record.has_tiktok,
                        has_gosuslugi=lead_record.has_gosuslugi,
                        lead_name=lead_record.name,
                        gosuslugi_name=lead_record.gosuslugi_name,
                        gosuslugi_surname=lead_record.gosuslugi_surname,
                        weights=settings,
                    )
                    lead_record.lead_score = score_res.score
                    lead_record.qualification_tier = score_res.tier
                
                db.add(lead_record)
                db.commit()
                db.refresh(lead_record)
                
                logger.info(f"Lead saved to database: {lead_record.id}")
                
                # Выгружаем данные в CRM/почту/телеграм
                if project:
                    await self._export_lead(lead_record, project, db)
                
            except Exception as e:
                logger.error(f"Failed to save lead to database: {e}")
                db.rollback()
        
        # Отправляем конверсию в Яндекс.Метрику (токен/счётчик из интеграции клиента или из env)
        try:
            client_id = lead.ym_uid or lead.client_ip or "unknown"
            if project and project.enable_metrica_export:
                oauth_token, counter_id = _get_metrica_credentials_from_project(db, project)
                await metrica_service.send_quality_lead(
                    client_id,
                    oauth_token=oauth_token,
                    counter_id=counter_id,
                )
        except Exception as e:
            logger.error(f"Failed to send Metrica conversion: {e}")
        
        return ValidationResult(
            success=True,
            lead_id=str(lead_record.id) if lead_record else None,
            execution_time_ms=round(execution_time, 2),
            phone_type=dadata.type if dadata else None,
            phone_provider=dadata.provider if dadata else None,
            phone_region=dadata.region if dadata else None,
            dadata_qc=dadata.qc if dadata else None,
            lead_score=getattr(lead_record, "lead_score", None) if lead_record else None,
            qualification_tier=getattr(lead_record, "qualification_tier", None) if lead_record else None,
        )


    async def _export_lead(
        self,
        lead_record: 'models.Lead',
        project: 'models.PhoneProject',
        db: Session
    ):
        """
        Выгружает заявку в CRM/почту/телеграм с пометками.
        """
        import httpx
        from datetime import datetime
        
        # Формируем данные для выгрузки (полный JSON для CRM / email)
        social_accounts_json = None
        if lead_record.social_accounts_data:
            try:
                social_accounts_json = json.loads(lead_record.social_accounts_data)
            except (json.JSONDecodeError, TypeError):
                social_accounts_json = lead_record.social_accounts_data

        export_data = {
            "lead_id": str(lead_record.id),
            "phone": lead_record.phone,
            "email": lead_record.email,
            "name": lead_record.name,
            "surname": lead_record.surname,
            "status": "проверено" if lead_record.is_verified else ("потенциальный спам" if lead_record.is_spam else "валидная заявка"),
            "is_verified": lead_record.is_verified,
            "is_spam": lead_record.is_spam,
            "phone_type": lead_record.phone_type,
            "phone_provider": lead_record.phone_provider,
            "phone_region": lead_record.phone_region,
            "phone_city": lead_record.phone_city,
            "has_telegram": lead_record.has_telegram,
            "has_whatsapp": lead_record.has_whatsapp,
            "has_viber": getattr(lead_record, "has_viber", None),
            "has_vk": lead_record.has_vk,
            "has_tiktok": lead_record.has_tiktok,
            "has_gosuslugi": lead_record.has_gosuslugi,
            "gosuslugi_name": lead_record.gosuslugi_name,
            "gosuslugi_surname": lead_record.gosuslugi_surname,
            "social_accounts": social_accounts_json,
            "lead_score": getattr(lead_record, "lead_score", None),
            "qualification_tier": getattr(lead_record, "qualification_tier", None),
            "utm_source": lead_record.utm_source,
            "utm_campaign": lead_record.utm_campaign,
            "created_at": lead_record.created_at.isoformat() if lead_record.created_at else None,
        }
        
        # Выгрузка в CRM (webhook)
        if project.crm_webhook_url and not lead_record.exported_to_crm:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        project.crm_webhook_url,
                        json=export_data,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code in (200, 201):
                        lead_record.exported_to_crm = True
                        logger.info(f"Lead exported to CRM: {lead_record.id}")
            except Exception as e:
                logger.error(f"Failed to export lead to CRM: {e}")
        
        # Выгрузка в почту
        if project.email_recipients and not lead_record.exported_to_email:
            try:
                recipients = json.loads(project.email_recipients) if project.email_recipients else []
                from lead_validator.services.email_sender import email_sender
                sent = await email_sender.send_lead_notification(recipients, export_data)
                if sent:
                    lead_record.exported_to_email = True
                    logger.info(f"Lead exported to email: {lead_record.id}")
            except Exception as e:
                logger.error(f"Failed to export lead to email: {e}")
        
        # Выгрузка в Telegram (если указан chat_id проекта)
        if project.telegram_chat_id and not lead_record.exported_to_telegram:
            try:
                message = f"📞 Новая заявка из проекта «{project.name}»\n\n"
                message += f"📱 Телефон: `{lead_record.phone}`\n"
                if lead_record.phone_type:
                    message += f"Тип: {lead_record.phone_type}\n"
                if lead_record.phone_provider:
                    message += f"Оператор: {lead_record.phone_provider}\n"
                if lead_record.phone_region:
                    message += f"Регион: {lead_record.phone_region}\n"
                if lead_record.phone_city:
                    message += f"Город: {lead_record.phone_city}\n"
                if lead_record.name:
                    message += f"👤 Имя: {lead_record.name}\n"
                if lead_record.email:
                    message += f"📧 Email: {lead_record.email}\n"
                msgr = []
                if getattr(lead_record, "has_telegram", None):
                    msgr.append("TG")
                if getattr(lead_record, "has_whatsapp", None):
                    msgr.append("WA")
                if getattr(lead_record, "has_viber", None):
                    msgr.append("Viber")
                if getattr(lead_record, "has_vk", None):
                    msgr.append("VK")
                if getattr(lead_record, "has_tiktok", None):
                    msgr.append("TikTok")
                if msgr:
                    message += f"💬 Мессенджеры: {', '.join(msgr)}\n"
                if getattr(lead_record, "lead_score", None) is not None:
                    message += f"📊 Скоринг: {lead_record.lead_score} ({getattr(lead_record, 'qualification_tier', '') or '-'})\n"
                if isinstance(social_accounts_json, dict):
                    links = []
                    tg = social_accounts_json.get("telegram") or {}
                    if isinstance(tg, dict) and tg.get("username"):
                        links.append(f"TG @{tg['username']}")
                    vk = social_accounts_json.get("vk") or {}
                    if isinstance(vk, dict) and vk.get("profile_url"):
                        links.append(f"VK {vk['profile_url']}")
                    if links:
                        message += "🔗 " + " | ".join(links) + "\n"
                if lead_record.utm_source or lead_record.utm_campaign:
                    message += f"🔗 UTM: source={lead_record.utm_source or '-'}, campaign={lead_record.utm_campaign or '-'}\n"
                message += f"🕐 {lead_record.created_at.strftime('%d.%m.%Y %H:%M') if lead_record.created_at else ''}\n"
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    telegram_token = settings.TELEGRAM_BOT_TOKEN
                    if telegram_token:
                        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                        await client.post(url, json={
                            "chat_id": project.telegram_chat_id,
                            "text": message,
                            "parse_mode": "Markdown"
                        })
                        lead_record.exported_to_telegram = True
                        logger.info(f"Lead exported to Telegram: {lead_record.id}")
            except Exception as e:
                logger.error(f"Failed to export lead to Telegram: {e}")
        
        # Обновляем timestamp выгрузки
        if any([lead_record.exported_to_crm, lead_record.exported_to_email, lead_record.exported_to_telegram]):
            lead_record.export_timestamp = datetime.now()
            db.commit()


# Глобальный экземпляр
lead_validator = LeadValidator()

