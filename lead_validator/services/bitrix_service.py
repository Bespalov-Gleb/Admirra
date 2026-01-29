"""
Интеграция с Bitrix24 CRM для проверки дубликатов контактов (Уровень 3 по ТЗ).

Перед созданием нового лида проверяет существующие контакты с таким телефоном или email.
Если контакт найден - не создавать новый лид, а обновить существующий.
"""

import logging
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.bitrix")


@dataclass
class BitrixDuplicateResult:
    """Результат поиска дубликатов в Bitrix24."""
    has_duplicate: bool = False
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    duplicate_type: Optional[str] = None  # phone, email


class BitrixService:
    """
    Сервис для работы с Bitrix24 API.
    
    Использует webhook URL для доступа к API без OAuth.
    """
    
    def __init__(self):
        self.webhook_url = settings.BITRIX24_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            logger.info("Bitrix24 integration disabled (no webhook URL)")
    
    async def find_duplicate_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по телефону через crm.duplicate.findbycomm.
        
        Args:
            phone: Номер телефона (нормализованный)
            
        Returns:
            Dict с данными контакта или None если не найден
        """
        if not self.enabled:
            return None
        
        try:
            # Нормализуем телефон (только цифры)
            digits_only = "".join(filter(str.isdigit, phone))
            if not digits_only or len(digits_only) < 10:
                return None
            
            url = f"{self.webhook_url}/crm.duplicate.findbycomm"
            params = {
                "type": "PHONE",
                "values": [digits_only]
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result"):
                        # Возвращаем первый найденный контакт
                        contacts = data["result"]
                        if contacts:
                            return contacts[0]
                elif response.status_code == 400:
                    # Нет дубликатов
                    return None
                else:
                    logger.warning(f"Bitrix24 API returned {response.status_code}: {response.text[:200]}")
                    
        except httpx.TimeoutException:
            logger.warning(f"Bitrix24 API timeout for phone {phone[:10]}...")
        except Exception as e:
            logger.error(f"Bitrix24 API error: {e}")
        
        return None
    
    async def find_duplicate_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Поиск контакта по email через crm.duplicate.findbycomm.
        
        Args:
            email: Email адрес
            
        Returns:
            Dict с данными контакта или None если не найден
        """
        if not self.enabled or not email:
            return None
        
        try:
            email_normalized = email.lower().strip()
            
            url = f"{self.webhook_url}/crm.duplicate.findbycomm"
            params = {
                "type": "EMAIL",
                "values": [email_normalized]
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result"):
                        # Возвращаем первый найденный контакт
                        contacts = data["result"]
                        if contacts:
                            return contacts[0]
                elif response.status_code == 400:
                    # Нет дубликатов
                    return None
                else:
                    logger.warning(f"Bitrix24 API returned {response.status_code}: {response.text[:200]}")
                    
        except httpx.TimeoutException:
            logger.warning(f"Bitrix24 API timeout for email {email[:20]}...")
        except Exception as e:
            logger.error(f"Bitrix24 API error: {e}")
        
        return None
    
    async def find_duplicates(self, phone: Optional[str] = None, email: Optional[str] = None) -> BitrixDuplicateResult:
        """
        Поиск дубликатов контакта по телефону и/или email.
        
        Args:
            phone: Номер телефона
            email: Email адрес
            
        Returns:
            BitrixDuplicateResult с результатом поиска
        """
        result = BitrixDuplicateResult()
        
        if not self.enabled:
            return result
        
        # Сначала проверяем телефон
        if phone:
            contact = await self.find_duplicate_by_phone(phone)
            if contact:
                result.has_duplicate = True
                result.contact_id = str(contact.get("ID", ""))
                result.contact_name = contact.get("NAME", "") or contact.get("TITLE", "")
                result.duplicate_type = "phone"
                logger.info(f"Found duplicate contact by phone: {result.contact_id}")
                return result
        
        # Затем проверяем email
        if email:
            contact = await self.find_duplicate_by_email(email)
            if contact:
                result.has_duplicate = True
                result.contact_id = str(contact.get("ID", ""))
                result.contact_name = contact.get("NAME", "") or contact.get("TITLE", "")
                result.duplicate_type = "email"
                logger.info(f"Found duplicate contact by email: {result.contact_id}")
                return result
        
        return result
    
    async def update_contact(self, contact_id: str, fields: Dict[str, Any]) -> bool:
        """
        Обновить существующий контакт в Bitrix24.
        
        Args:
            contact_id: ID контакта
            fields: Поля для обновления
            
        Returns:
            True если успешно обновлено
        """
        if not self.enabled:
            return False
        
        try:
            url = f"{self.webhook_url}/crm.contact.update"
            params = {
                "id": contact_id,
                "fields": fields
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result"):
                        logger.info(f"Updated Bitrix24 contact: {contact_id}")
                        return True
                else:
                    logger.warning(f"Bitrix24 update returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"Bitrix24 update error: {e}")
        
        return False
    
    async def create_deal(self, contact_id: str, title: str, fields: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Создать новое дело (сделку) для существующего контакта.
        
        Args:
            contact_id: ID контакта
            title: Название дела
            fields: Дополнительные поля
            
        Returns:
            ID созданного дела или None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.webhook_url}/crm.deal.add"
            params = {
                "fields": {
                    "TITLE": title,
                    "CONTACT_ID": contact_id,
                    **(fields or {})
                }
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=params)
                
                if response.status_code == 200:
                    data = response.json()
                    deal_id = data.get("result")
                    if deal_id:
                        logger.info(f"Created Bitrix24 deal: {deal_id} for contact {contact_id}")
                        return str(deal_id)
                else:
                    logger.warning(f"Bitrix24 deal creation returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"Bitrix24 deal creation error: {e}")
        
        return None


# Глобальный экземпляр
bitrix_service = BitrixService()

