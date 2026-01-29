import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class MyTargetAPI:
    """
    API клиент для работы с myTarget API.
    
    Использует Authorization Code Grant для получения токена.
    Для песочницы: https://target-sandbox.my.com/api/v2
    Для боевого окружения: https://target.my.com/api/v2 или https://target.vk.ru/api/v2
    """
    
    def __init__(self, access_token: str, account_id: str = None, use_sandbox: bool = True):
        """
        Инициализация клиента myTarget API.
        
        Args:
            access_token: OAuth токен доступа
            account_id: ID рекламного кабинета (опционально)
            use_sandbox: Использовать ли песочницу (по умолчанию True)
        """
        if use_sandbox:
            self.base_url = "https://target-sandbox.my.com/api/v2"
        else:
            # Для боевого окружения можно использовать target.my.com или target.vk.ru
            self.base_url = os.getenv("MYTARGET_API_URL", "https://target.my.com/api/v2")
        
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
        self.account_id = account_id

    async def get_campaigns(self) -> List[Dict[str, Any]]:
        """
        Получает список всех кампаний (ad_plans).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID кампании
            - name: str - название кампании
            - status: str - статус кампании
        """
        url = f"{self.base_url}/ad_plans.json"
        params = {}
        if self.account_id:
            params["client_id"] = self.account_id
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "id": str(item["id"]),
                            "name": item.get("name", f"Campaign {item['id']}"),
                            "status": item.get("status", "unknown")
                        }
                        for item in data.get("items", [])
                    ]
                else:
                    logger.error(f"Failed to fetch myTarget campaigns: {response.status_code} - {response.text[:200]}")
                    raise Exception(f"Failed to fetch myTarget campaigns: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error fetching myTarget campaigns: {e}")
            raise e

    async def get_statistics(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Получает статистику по кампаниям за указанный период.
        Автоматически разбивает диапазон дат на чанки по 90 дней для соблюдения лимитов API.
        
        Args:
            date_from: Начальная дата в формате YYYY-MM-DD
            date_to: Конечная дата в формате YYYY-MM-DD
            
        Returns:
            List[Dict] с полями:
            - date: str - дата
            - campaign_id: str - ID кампании
            - campaign_name: str - название кампании
            - impressions: int - показы
            - clicks: int - клики
            - cost: float - стоимость
            - conversions: int - конверсии
        """
        # Получаем названия кампаний
        campaigns = await self.get_campaigns()
        names_map = {int(c["id"]): c["name"] for c in campaigns}
        
        # Разбиваем даты на чанки
        date_chunks = self._split_date_range(date_from, date_to, 90)
        all_results = []

        async with httpx.AsyncClient() as client:
            for d_from, d_to in date_chunks:
                url = f"{self.base_url}/statistics/ad_plans/day.json"
                params = {
                    "date_from": d_from,
                    "date_to": d_to,
                    "metrics": "base"
                }
                if self.account_id:
                    params["client_id"] = self.account_id

                try:
                    # Увеличиваем таймаут для больших периодов
                    date_range_days = (datetime.strptime(d_to, "%Y-%m-%d") - datetime.strptime(d_from, "%Y-%m-%d")).days
                    if date_range_days > 90:
                        timeout_seconds = min(600.0, 120.0 + (date_range_days - 90) * 2)
                    else:
                        timeout_seconds = 120.0
                    
                    response = await client.get(url, params=params, headers=self.headers, timeout=timeout_seconds)
                    if response.status_code == 200:
                        chunk_data = self._parse_response(response.json(), names_map)
                        all_results.extend(chunk_data)
                    elif response.status_code == 400:
                        logger.warning(f"myTarget API returned 400 for range {d_from}-{d_to}. Likely old data or invalid params. Response: {response.text[:200]}")
                    else:
                        logger.error(f"myTarget API error for range {d_from}-{d_to}: {response.status_code} - {response.text[:200]}")
                except Exception as e:
                    logger.error(f"myTarget API Exception for range {d_from}-{d_to}: {e}")
                
                # Задержка для избежания rate limiting
                await asyncio.sleep(1)
                    
        return all_results

    def _split_date_range(self, date_from: str, date_to: str, interval: int = 90) -> List[tuple]:
        """Разбивает диапазон дат на меньшие чанки."""
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")
        
        chunks = []
        curr = start
        while curr <= end:
            chunk_end = min(curr + timedelta(days=interval), end)
            chunks.append((curr.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
            curr = chunk_end + timedelta(days=1)
        return chunks

    def _parse_response(self, data: Dict[str, Any], names_map: Dict[int, str]) -> List[Dict[str, Any]]:
        """
        Парсит JSON ответ myTarget API, используя names_map для названий кампаний.
        """
        results = []
        items = data.get("items", [])
        for item in items:
            campaign_id = item.get("id")
            campaign_name = names_map.get(campaign_id, f"Campaign {campaign_id}")
            rows = item.get("rows", [])
            for row in rows:
                base = row.get("base", {})
                row_date = row.get("date")
                if not row_date:
                    continue
                    
                results.append({
                    "date": row_date,
                    "campaign_id": str(campaign_id) if campaign_id else "",
                    "campaign_name": campaign_name,
                    "impressions": int(base.get("shows", 0)),
                    "clicks": int(base.get("clicks", 0)),
                    "cost": float(base.get("spent", 0)),
                    "conversions": int(base.get("goals", 0))
                })
        return results
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных рекламных аккаунтов (кабинетов).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта
            - name: str - название аккаунта
            - status: str - статус аккаунта
        """
        url = f"{self.base_url}/ad_accounts.json"
        params = {}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    return [
                        {
                            "id": str(item.get("id")),
                            "name": item.get("name", f"Аккаунт {item.get('id')}"),
                            "status": item.get("status", "unknown")
                        }
                        for item in items
                    ]
                else:
                    logger.warning(f"Failed to fetch myTarget accounts: {response.status_code} - {response.text[:200]}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching myTarget accounts: {e}")
            return []
    
    async def get_profiles(self) -> List[Dict[str, Any]]:
        """
        Получает список всех доступных профилей (аккаунтов) для выбора.
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта
            - name: str - название
            - type: str - "personal"
        """
        profiles = []
        seen_ids = set()
        
        try:
            accounts = await self.get_accounts()
            for account in accounts:
                account_id = account.get("id")
                if account_id and account_id not in seen_ids:
                    profiles.append({
                        "id": account_id,
                        "name": account.get("name", f"Аккаунт {account_id}"),
                        "type": "personal"
                    })
                    seen_ids.add(account_id)
                    logger.info(f"✅ Added myTarget account: {account_id}")
        except Exception as e:
            logger.warning(f"Failed to fetch myTarget accounts: {e}")
        
        # Fallback: если ничего не найдено, возвращаем текущий account_id если он есть
        if not profiles and self.account_id:
            profiles.append({
                "id": str(self.account_id),
                "name": f"Аккаунт ({self.account_id})",
                "type": "personal"
            })
            logger.info(f"✅ Added fallback myTarget account: {self.account_id}")
        
        return profiles
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        Получает баланс рекламного кабинета myTarget.
        
        Returns:
            Dict с полями:
            - balance: float - баланс в валюте кабинета
            - currency: str - код валюты (RUB, USD, EUR, etc.)
            Или None при ошибке
        """
        url = f"{self.base_url}/ad_accounts.json"
        params = {}
        if self.account_id:
            params["client_id"] = self.account_id
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items and len(items) > 0:
                        account = items[0]
                        balance = account.get("balance") or account.get("amount") or account.get("funds")
                        currency = account.get("currency", "RUB")
                        
                        if balance is not None:
                            try:
                                balance_float = float(balance) if isinstance(balance, str) else balance
                                logger.info(f"myTarget balance: {balance_float} {currency}")
                                return {
                                    "balance": balance_float,
                                    "currency": currency
                                }
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to parse myTarget balance value: {balance}, error: {e}")
                                return None
                else:
                    logger.warning(f"Failed to fetch myTarget balance: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.warning(f"Error fetching myTarget balance: {e}")
            return None

