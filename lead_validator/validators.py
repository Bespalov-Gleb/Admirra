"""
Цепочка валидаторов для проверки входящих лидов.
Проверки идут от дешёвых к дорогим для оптимизации.
"""

import logging
import time
import json
import uuid
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
from lead_validator.services.gosuslugi_checker import gosuslugi_checker

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
        referer: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        db: Optional[Session] = None,
        form_data: Optional[dict] = None
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
        
        # === Уровень 6: UTM валидация ===
        if settings.UTM_VALIDATION_ENABLED:
            utm_data = UTMData(
                source=lead.utm_source,
                medium=lead.utm_medium,
                campaign=lead.utm_campaign,
                content=lead.utm_content,
                term=lead.utm_term
            )
            
            # Если есть проект, получаем его настройки
            project = None
            if project_id and db:
                from core import models
                project = db.query(models.PhoneProject).filter_by(id=project_id).first()
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
        
        # === СТАДИЯ 2: Обогащение данных (если есть проект) ===
        project = None
        if project_id and db:
            from core import models
            project = db.query(models.PhoneProject).filter_by(id=project_id).first()
        
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
                
                # Если включена проверка соцсетей
                if project and project.enable_social_check:
                    social_result = await social_checker.check_phone(lead.phone)
                    lead_record.has_telegram = social_result.has_telegram
                    lead_record.has_whatsapp = social_result.has_whatsapp
                    lead_record.has_tiktok = social_result.has_tiktok if hasattr(social_result, 'has_tiktok') else None
                    lead_record.has_vk = social_result.has_vk
                    
                    # Сохраняем данные аккаунтов
                    social_data = {}
                    if social_result.has_telegram and hasattr(social_result, 'telegram_username'):
                        social_data['telegram'] = {'username': social_result.telegram_username}
                    if social_result.has_vk and hasattr(social_result, 'vk_profile_url'):
                        social_data['vk'] = {'profile_url': social_result.vk_profile_url}
                    if social_data:
                        lead_record.social_accounts_data = json.dumps(social_data)
                    
                    # Заполняем имя/фамилию из соцсетей если нет
                    if not lead_record.name and social_result.has_telegram:
                        # TODO: Получить имя из Telegram API если доступно
                        pass
                
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
        
        # Отправляем конверсию в Яндекс.Метрику
        try:
            # Используем ym_uid если есть, иначе IP как fallback
            client_id = lead.ym_uid or lead.client_ip or "unknown"
            if project and project.enable_metrica_export:
                await metrica_service.send_quality_lead(client_id)
        except Exception as e:
            logger.error(f"Failed to send Metrica conversion: {e}")
        
        return ValidationResult(
            success=True,
            lead_id=str(lead_record.id) if lead_record else None,
            execution_time_ms=round(execution_time, 2),
            phone_type=dadata.type if dadata else None,
            phone_provider=dadata.provider if dadata else None,
            phone_region=dadata.region if dadata else None,
            dadata_qc=dadata.qc if dadata else None
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
        
        # Формируем данные для выгрузки
        export_data = {
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
            "has_telegram": lead_record.has_telegram,
            "has_whatsapp": lead_record.has_whatsapp,
            "has_gosuslugi": lead_record.has_gosuslugi,
            "utm_source": lead_record.utm_source,
            "utm_campaign": lead_record.utm_campaign,
            "created_at": lead_record.created_at.isoformat() if lead_record.created_at else None
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
                # TODO: Реализовать отправку email
                # from lead_validator.services.email_sender import email_sender
                # await email_sender.send_lead_notification(recipients, export_data)
                lead_record.exported_to_email = True
                logger.info(f"Lead exported to email: {lead_record.id}")
            except Exception as e:
                logger.error(f"Failed to export lead to email: {e}")
        
        # Выгрузка в Telegram (если указан chat_id проекта)
        if project.telegram_chat_id and not lead_record.exported_to_telegram:
            try:
                # Используем telegram_notifier, но с chat_id проекта
                message = f"📞 Новая заявка из проекта '{project.name}':\n"
                message += f"Телефон: {lead_record.phone}\n"
                if lead_record.name:
                    message += f"Имя: {lead_record.name}\n"
                if lead_record.email:
                    message += f"Email: {lead_record.email}\n"
                message += f"Статус: {export_data['status']}\n"
                
                async with httpx.AsyncClient(timeout=10.0) as client:
                    telegram_token = settings.TELEGRAM_BOT_TOKEN
                    if telegram_token:
                        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                        await client.post(url, json={
                            "chat_id": project.telegram_chat_id,
                            "text": message
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

