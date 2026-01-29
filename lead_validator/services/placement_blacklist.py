"""
Динамический чёрный список площадок (Уровень 8 по ТЗ).

Автоматически добавляет площадки с >70-80% мусора на 2-3 недели в чёрный список.
Хранится в Redis с TTL.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from lead_validator.services.redis_service import redis_service
from lead_validator.services.analytics import analytics_service, SourceStats
from lead_validator.config import settings

logger = logging.getLogger("lead_validator.placement_blacklist")


class PlacementBlacklist:
    """
    Управление динамическим чёрным списком площадок.
    
    Площадка добавляется в чёрный список если:
    - >70-80% мусора на протяжении 2-3 недель
    - Минимум 10 заявок за период
    """
    
    def __init__(self):
        self.blacklist_threshold_percent = settings.PLACEMENT_BLACKLIST_THRESHOLD
        self.blacklist_min_leads = settings.PLACEMENT_BLACKLIST_MIN_LEADS
        self.blacklist_ttl_days = settings.PLACEMENT_BLACKLIST_TTL_DAYS
        
    def _get_placement_key(self, utm_source: str, utm_campaign: str, utm_content: str) -> str:
        """
        Создать ключ для площадки.
        
        Формат: placement:{source}:{campaign}:{content}
        """
        return f"placement:{utm_source or 'direct'}:{utm_campaign or 'none'}:{utm_content or 'none'}"
    
    async def is_blacklisted(self, utm_source: Optional[str], utm_campaign: Optional[str], utm_content: Optional[str]) -> bool:
        """
        Проверить, находится ли площадка в чёрном списке.
        
        Args:
            utm_source: Источник трафика
            utm_campaign: Кампания
            utm_content: Площадка (ID в РСЯ)
            
        Returns:
            True если площадка в чёрном списке
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            key = self._get_placement_key(
                utm_source or "direct",
                utm_campaign or "none",
                utm_content or "none"
            )
            exists = await client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Redis blacklist check error: {e}")
            return False
    
    async def add_to_blacklist(
        self,
        utm_source: str,
        utm_campaign: str,
        utm_content: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Добавить площадку в чёрный список.
        
        Args:
            utm_source: Источник трафика
            utm_campaign: Кампания
            utm_content: Площадка
            reason: Причина добавления (опционально)
            
        Returns:
            True если успешно добавлено
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            key = self._get_placement_key(utm_source, utm_campaign, utm_content)
            ttl_seconds = self.blacklist_ttl_days * 24 * 3600
            
            value = reason or f"auto_blacklisted_{datetime.now().isoformat()}"
            await client.setex(key, ttl_seconds, value)
            
            logger.info(
                f"Added placement to blacklist: {utm_source}/{utm_campaign}/{utm_content} "
                f"(TTL: {self.blacklist_ttl_days} days)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add placement to blacklist: {e}")
            return False
    
    async def remove_from_blacklist(
        self,
        utm_source: str,
        utm_campaign: str,
        utm_content: str
    ) -> bool:
        """
        Удалить площадку из чёрного списка.
        
        Args:
            utm_source: Источник трафика
            utm_campaign: Кампания
            utm_content: Площадка
            
        Returns:
            True если успешно удалено
        """
        client = await redis_service._get_client()
        if client is None:
            return False
        
        try:
            key = self._get_placement_key(utm_source, utm_campaign, utm_content)
            await client.delete(key)
            logger.info(f"Removed placement from blacklist: {utm_source}/{utm_campaign}/{utm_content}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove placement from blacklist: {e}")
            return False
    
    async def update_blacklist(self) -> int:
        """
        Обновить чёрный список на основе статистики.
        
        Анализирует источники трафика и добавляет плохие площадки в чёрный список.
        
        Returns:
            Количество добавленных площадок
        """
        logger.info("Updating placement blacklist...")
        
        added_count = 0
        
        try:
            # Получаем плохие источники (с высоким процентом мусора)
            bad_sources = analytics_service.get_bad_sources(
                min_leads=self.blacklist_min_leads,
                min_rejection_rate=self.blacklist_threshold_percent
            )
            
            for source in bad_sources:
                # Проверяем, не в чёрном списке ли уже
                is_blacklisted = await self.is_blacklisted(
                    source.source,
                    source.campaign,
                    source.content
                )
                
                if not is_blacklisted:
                    # Добавляем в чёрный список
                    reason = (
                        f"rejection_rate_{source.rejection_rate:.1f}%_"
                        f"leads_{source.total_leads}_rejected_{source.rejected_leads}"
                    )
                    
                    success = await self.add_to_blacklist(
                        source.source,
                        source.campaign,
                        source.content,
                        reason
                    )
                    
                    if success:
                        added_count += 1
                        logger.info(
                            f"Auto-blacklisted placement: {source.source}/{source.campaign}/{source.content} "
                            f"({source.rejection_rate:.1f}% rejection rate)"
                        )
            
            logger.info(f"Blacklist update completed: {added_count} new placements added")
            
        except Exception as e:
            logger.error(f"Error updating blacklist: {e}", exc_info=True)
        
        return added_count
    
    async def get_blacklist(self) -> List[Dict[str, str]]:
        """
        Получить список всех площадок в чёрном списке.
        
        Returns:
            Список словарей с информацией о площадках
        """
        client = await redis_service._get_client()
        if client is None:
            return []
        
        try:
            # Получаем все ключи с префиксом placement:
            keys = await client.keys("placement:*")
            blacklist = []
            
            for key in keys:
                value = await client.get(key)
                ttl = await client.ttl(key)
                
                # Парсим ключ: placement:{source}:{campaign}:{content}
                parts = key.split(":")
                if len(parts) >= 4:
                    source = parts[1]
                    campaign = parts[2]
                    content = ":".join(parts[3:])  # На случай если content содержит :
                    
                    blacklist.append({
                        "source": source,
                        "campaign": campaign,
                        "content": content,
                        "reason": value or "",
                        "ttl_seconds": ttl,
                        "expires_in_days": ttl // (24 * 3600) if ttl > 0 else 0
                    })
            
            return blacklist
            
        except Exception as e:
            logger.error(f"Error getting blacklist: {e}")
            return []


# Глобальный экземпляр
placement_blacklist = PlacementBlacklist()

