"""
Сервис интеграции с Яндекс.Метрикой.
Отправка офлайн-конверсий для связи онлайн-визитов с заявками.

API: https://api-metrica.yandex.net/management/v1/counter/{counterId}/offline_conversions/upload
"""

import logging
import io
import csv
from datetime import datetime
from typing import Optional, Literal
from dataclasses import dataclass

import httpx

from lead_validator.config import settings

logger = logging.getLogger("lead_validator.metrica")


# Типы целей для отправки в Метрику
GoalType = Literal["quality_lead", "potential_spam", "all_leads"]


@dataclass
class ConversionData:
    """Данные для отправки конверсии в Метрику."""
    client_id: str  # ID посетителя (из cookie _ym_uid или clientId)
    goal_name: str  # Название цели
    datetime_str: str  # Дата в формате YYYY-MM-DD HH:MM:SS
    price: Optional[float] = None  # Ценность конверсии
    currency: str = "RUB"


class MetricaService:
    """
    Сервис для отправки офлайн-конверсий в Яндекс.Метрику.
    
    Позволяет связать заявки с сессиями на сайте для оптимизации
    рекламных кампаний в Яндекс.Директ.
    
    Типы целей:
    - quality_lead: качественный лид (прошёл все проверки)
    - potential_spam: потенциальный спам (отклонён)
    - all_leads: все лиды (для общей статистики)
    """
    
    def __init__(self):
        self.enabled = settings.METRICA_ENABLED
        self.counter_id = settings.METRICA_COUNTER_ID
        self.oauth_token = settings.METRICA_OAUTH_TOKEN
        
        self.base_url = "https://api-metrica.yandex.net/management/v1"
        
        # Маппинг типов целей на названия в Метрике
        self.goal_names = {
            "quality_lead": "качественный_лид",
            "potential_spam": "потенциально_спам",
            "all_leads": "все_лиды"
        }
        
        if self.enabled:
            if not self.counter_id:
                logger.warning("METRICA_COUNTER_ID not set, disabling Metrica")
                self.enabled = False
            elif not self.oauth_token:
                logger.warning("METRICA_OAUTH_TOKEN not set, disabling Metrica")
                self.enabled = False
            else:
                logger.info(f"Metrica enabled for counter: {self.counter_id}")
        else:
            logger.info("Metrica integration disabled")
    
    async def send_conversion(
        self,
        client_id: str,
        goal_type: GoalType = "all_leads",
        price: Optional[float] = None,
        conversion_time: Optional[datetime] = None
    ) -> bool:
        """
        Отправить офлайн-конверсию в Яндекс.Метрику.
        
        Args:
            client_id: ID посетителя (_ym_uid cookie или IP как fallback)
            goal_type: Тип цели (quality_lead, potential_spam, all_leads)
            price: Ценность конверсии (опционально)
            conversion_time: Время конверсии (по умолчанию сейчас)
            
        Returns:
            True если успешно отправлено, False при ошибке
        """
        if not self.enabled:
            logger.debug("Metrica disabled, skipping conversion")
            return False
        
        if not client_id:
            logger.warning("No client_id provided, skipping conversion")
            return False
        
        # Время конверсии
        dt = conversion_time or datetime.now()
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Название цели
        goal_name = self.goal_names.get(goal_type, goal_type)
        
        # Формируем CSV данные
        csv_content = self._build_csv(client_id, goal_name, dt_str, price)
        
        try:
            return await self._upload_conversions(csv_content)
        except Exception as e:
            logger.error(f"Failed to send conversion to Metrica: {e}")
            return False
    
    async def send_quality_lead(self, client_id: str, price: Optional[float] = None) -> bool:
        """Отправить конверсию 'качественный лид'."""
        # Отправляем обе цели: качественный_лид и все_лиды
        result1 = await self.send_conversion(client_id, "quality_lead", price)
        result2 = await self.send_conversion(client_id, "all_leads", price)
        return result1 or result2
    
    async def send_spam_lead(self, client_id: str) -> bool:
        """Отправить конверсию 'потенциальный спам'."""
        # Отправляем обе цели: потенциально_спам и все_лиды
        result1 = await self.send_conversion(client_id, "potential_spam")
        result2 = await self.send_conversion(client_id, "all_leads")
        return result1 or result2
    
    def _build_csv(
        self, 
        client_id: str, 
        goal_name: str, 
        datetime_str: str,
        price: Optional[float] = None
    ) -> str:
        """Сформировать CSV для загрузки в Метрику."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        if price is not None:
            writer.writerow(["ClientId", "Target", "DateTime", "Price", "Currency"])
            writer.writerow([client_id, goal_name, datetime_str, price, "RUB"])
        else:
            writer.writerow(["ClientId", "Target", "DateTime"])
            writer.writerow([client_id, goal_name, datetime_str])
        
        return output.getvalue()
    
    async def _upload_conversions(self, csv_content: str) -> bool:
        """
        Загрузить CSV с конверсиями в Метрику.
        
        API endpoint: POST /management/v1/counter/{counterId}/offline_conversions/upload
        """
        url = f"{self.base_url}/counter/{self.counter_id}/offline_conversions/upload"
        
        headers = {
            "Authorization": f"OAuth {self.oauth_token}"
        }
        
        # Multipart form data с CSV файлом
        files = {
            "file": ("conversions.csv", csv_content, "text/csv")
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, files=files)
            
            if response.status_code == 200:
                data = response.json()
                upload_id = data.get("upload_id")
                logger.info(f"Conversion uploaded successfully, upload_id: {upload_id}")
                return True
            else:
                logger.error(
                    f"Metrica API error: {response.status_code} - {response.text}"
                )
                return False
    
    async def test_connection(self) -> dict:
        """
        Тест подключения к Метрике.
        Возвращает информацию о счётчике.
        """
        if not self.enabled:
            return {
                "ok": False,
                "error": "Metrica integration disabled",
                "config": {
                    "counter_id": self.counter_id or "not set",
                    "token_set": bool(self.oauth_token)
                }
            }
        
        url = f"{self.base_url}/counter/{self.counter_id}"
        headers = {"Authorization": f"OAuth {self.oauth_token}"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    counter = data.get("counter", {})
                    return {
                        "ok": True,
                        "counter_id": self.counter_id,
                        "counter_name": counter.get("name"),
                        "site": counter.get("site"),
                        "goals_count": len(counter.get("goals", []))
                    }
                else:
                    return {
                        "ok": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)
            }


# Глобальный экземпляр
metrica_service = MetricaService()
