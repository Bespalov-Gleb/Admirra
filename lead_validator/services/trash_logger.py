"""
Логирование отклонённых заявок для аналитики.
Поддерживает Airtable и локальный SQLite fallback.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from lead_validator.config import settings
from lead_validator.schemas import RejectedLead

logger = logging.getLogger("lead_validator.trash_logger")


class TrashLogger:
    """
    Сохранение отклонённых заявок для анализа источников мусора.
    
    Порядок приоритета:
    1. Airtable (если настроен)
    2. SQLite (локальная БД)
    3. JSON файл (fallback)
    """
    
    def __init__(self):
        self.airtable_enabled = bool(
            settings.AIRTABLE_API_KEY and 
            settings.AIRTABLE_BASE_ID
        )
        self._init_local_storage()
        
    def _init_local_storage(self):
        """Инициализация локального хранилища"""
        self.log_dir = Path("logs/rejected_leads")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    async def log_rejected(self, lead: RejectedLead) -> bool:
        """
        Сохраняет отклонённую заявку.
        
        Returns:
            True если успешно сохранено
        """
        # Пробуем Airtable
        if self.airtable_enabled:
            success = await self._log_to_airtable(lead)
            if success:
                return True
                
        # Fallback на локальный файл
        return await self._log_to_file(lead)
    
    async def _log_to_airtable(self, lead: RejectedLead) -> bool:
        """
        Отправка в Airtable.
        
        TODO: Реализовать после получения ключей Airtable.
        Лимит: 5 запросов в секунду, нужен bulk-insert для высокой нагрузки.
        """
        try:
            import httpx
            
            url = (
                f"https://api.airtable.com/v0/"
                f"{settings.AIRTABLE_BASE_ID}/{settings.AIRTABLE_TABLE_NAME}"
            )
            
            headers = {
                "Authorization": f"Bearer {settings.AIRTABLE_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Преобразуем в формат Airtable
            fields = {
                "Phone": lead.phone,
                "Email": lead.email or "",
                "Name": lead.name or "",
                "Rejection Reason": lead.rejection_reason,
                "Rejection Details": lead.rejection_details or "",
                "UTM Source": lead.utm_source or "",
                "UTM Medium": lead.utm_medium or "",
                "UTM Campaign": lead.utm_campaign or "",
                "Client IP": lead.client_ip or "",
                "Created At": lead.created_at.isoformat(),
                "DaData QC": lead.dadata_qc if lead.dadata_qc is not None else "",
                "Phone Type": lead.phone_type or ""
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"fields": fields}
                )
                
                if response.status_code in (200, 201):
                    logger.info(f"Rejected lead logged to Airtable: {lead.phone}")
                    return True
                else:
                    logger.error(
                        f"Airtable error: {response.status_code} - {response.text}"
                    )
                    
        except Exception as e:
            logger.error(f"Airtable logging error: {e}")
            
        return False
    
    async def _log_to_file(self, lead: RejectedLead) -> bool:
        """
        Fallback: сохранение в локальный JSON файл.
        Файлы разделены по датам для удобства.
        """
        try:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            file_path = self.log_dir / f"rejected_{date_str}.jsonl"
            
            # Сериализуем в JSON
            record = lead.model_dump()
            record["created_at"] = record["created_at"].isoformat()
            
            # Append в JSONL файл (каждая строка — JSON объект)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                
            logger.debug(f"Rejected lead logged to file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"File logging error: {e}")
            return False
    
    async def get_stats(self, date: Optional[str] = None) -> dict:
        """
        Получить статистику отклонённых заявок за дату.
        
        Args:
            date: Дата в формате YYYY-MM-DD, по умолчанию сегодня
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
            
        file_path = self.log_dir / f"rejected_{date}.jsonl"
        
        stats = {
            "date": date,
            "total": 0,
            "by_reason": {}
        }
        
        if not file_path.exists():
            return stats
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line.strip())
                    stats["total"] += 1
                    
                    reason = record.get("rejection_reason", "unknown")
                    stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1
                    
        except Exception as e:
            logger.error(f"Stats reading error: {e}")
            
        return stats


# Глобальный экземпляр
trash_logger = TrashLogger()

