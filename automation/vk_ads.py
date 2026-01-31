import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VKAdsAPI:
    def __init__(self, access_token: str, account_id: str = None):
        self.base_url = "https://ads.vk.com/api/v2" # Example base URL
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
        self.account_id = account_id

    async def get_campaigns(self) -> List[Dict[str, Any]]:
        """
        Fetches the list of all campaigns (AdPlans).
        """
        url = f"{self.base_url}/ad_plans.json"
        params = {}
        if self.account_id:
            params["client_id"] = self.account_id
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "id": str(item["id"]),
                            "name": item["name"],
                            "status": item.get("status")
                        }
                        for item in data.get("items", [])
                    ]
                else:
                    raise Exception(f"Failed to fetch VK campaigns: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error fetching VK campaigns: {e}")
            raise e

    async def get_statistics(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Fetches statistics and maps campaign IDs to names.
        Automatically splits date ranges into 90-day chunks to satisfy VK API limits.
        """
        # Fetch names first
        campaigns = await self.get_campaigns()
        names_map = {int(c["id"]): c["name"] for c in campaigns}
        
        # Split dates into chunks
        date_chunks = self._split_date_range(date_from, date_to, 90)
        all_results = []

        async with httpx.AsyncClient() as client:
            for d_from, d_to in date_chunks:
                # VK Ads v2 terminology: Campaigns are 'ad_plans'
                url = f"{self.base_url}/statistics/ad_plans/day.json"
                params = {
                    "date_from": d_from,
                    "date_to": d_to,
                    "metrics": "base"
                }
                if self.account_id:
                    params["client_id"] = self.account_id

                try:
                    # Увеличиваем таймаут для больших периодов (90+ дней)
                    date_range_days = (datetime.strptime(d_to, "%Y-%m-%d") - datetime.strptime(d_from, "%Y-%m-%d")).days
                    if date_range_days > 90:
                        timeout_seconds = min(600.0, 120.0 + (date_range_days - 90) * 2)  # Максимум 10 минут
                    else:
                        timeout_seconds = 120.0
                    
                    response = await client.get(url, params=params, headers=self.headers, timeout=timeout_seconds)
                    if response.status_code == 200:
                        chunk_data = self._parse_response(response.json(), names_map)
                        all_results.extend(chunk_data)
                    elif response.status_code == 400:
                        # VK often returns 400 for dates older than 12 months or invalid params.
                        # We log it but continue with other chunks.
                        logger.warning(f"VK Ads API returned 400 for range {d_from}-{d_to}. Likely old data or invalid params. Response: {response.text}")
                    else:
                        logger.error(f"VK Ads API error for range {d_from}-{d_to}: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.error(f"VK Ads API Exception for range {d_from}-{d_to}: {e}")
                
                # Sleep to avoid 429 Too Many Requests (VK limit is strict)
                await asyncio.sleep(1)
                    
        return all_results

    def _split_date_range(self, date_from: str, date_to: str, interval: int = 90) -> List[tuple]:
        """Splits a date range into smaller chunks."""
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
        Parses VK API JSON response using names_map for campaign names.
        """
        results = []
        items = data.get("items", [])
        for item in items:
            campaign_id = item.get("id")
            campaign_name = names_map.get(campaign_id, f"Campaign {campaign_id}")
            rows = item.get("rows", [])
            for row in rows:
                base = row.get("base", {})
                # Get date - it's at the row level
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
        
        VK Ads API endpoint: /api/v2/ad_accounts.json
        Возвращает список всех доступных рекламных кабинетов для пользователя.
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта (нормализованный числовой ID)
            - name: str - название аккаунта
            - status: str - статус аккаунта
        """
        url = f"{self.base_url}/ad_accounts.json"
        accounts = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 VK Ads API returned {len(items)} account(s) from ad_accounts.json")
                    
                    for item in items:
                        raw_id = item.get("id")
                        raw_id_str = str(raw_id)
                        
                        # Нормализуем account_id (извлекаем числовой ID из формата "vkads_592676405@vk@8493881")
                        import re
                        account_id = None
                        
                        if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                            # Формат: "vkads_592676405@vk@8493881" -> извлекаем "592676405"
                            match = re.search(r'vkads_(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                            else:
                                # Fallback: извлекаем первую числовую последовательность
                                match = re.search(r'(\d+)', raw_id_str)
                                if match:
                                    account_id = match.group(1)
                        elif raw_id_str.isdigit():
                            account_id = raw_id_str
                        else:
                            # Пытаемся извлечь любую числовую последовательность
                            match = re.search(r'(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        
                        if account_id:
                            account_name = item.get("name", f"Аккаунт {account_id}")
                            account_status = item.get("status", "active")
                            
                            accounts.append({
                                "id": account_id,
                                "name": account_name,
                                "status": account_status
                            })
                            
                            logger.info(f"✅ Added VK account: id={account_id}, name='{account_name}', status={account_status}")
                        else:
                            logger.warning(f"⚠️ Could not extract numeric ID from: '{raw_id_str}', skipping")
                    
                    if accounts:
                        logger.info(f"✅ Successfully retrieved {len(accounts)} VK account(s)")
                        return accounts
                    else:
                        logger.warning("⚠️ No valid accounts found in response")
                        
                elif response.status_code == 404:
                    logger.warning("⚠️ VK Ads API endpoint /ad_accounts.json returned 404 (endpoint may not be available for this account type)")
                else:
                    logger.warning(f"⚠️ VK Ads API returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching VK accounts: {e}")
        
        # Fallback: Если account_id задан в конструкторе, используем его
        if self.account_id:
            account_id_str = str(self.account_id)
            # Нормализуем account_id, если он в формате "vkads_XXX@vk@YYY"
            import re
            if '@vk@' in account_id_str or account_id_str.startswith('vkads_'):
                match = re.search(r'vkads_(\d+)', account_id_str)
                if match:
                    account_id_str = match.group(1)
            
            accounts.append({
                "id": account_id_str,
                "name": f"Аккаунт {account_id_str}",
                "status": "active"
            })
            logger.info(f"✅ Using account_id from constructor as fallback: {account_id_str}")
        
        return accounts
    
    async def get_agency_clients(self) -> List[Dict[str, Any]]:
        """
        Получает список клиентов агентского аккаунта (если токен принадлежит агентству).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID клиента
            - name: str - название клиента
            - status: str - статус клиента
        """
        url = f"{self.base_url}/agency/clients.json"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    return [
                        {
                            "id": str(item.get("id")),
                            "name": item.get("name", f"Клиент {item.get('id')}"),
                            "status": item.get("status", "unknown")
                        }
                        for item in items
                    ]
                elif response.status_code == 403:
                    # 403 означает, что это не агентский аккаунт - это нормально
                    logger.debug("VK account is not an agency account (403)")
                    return []
                else:
                    logger.warning(f"Failed to fetch VK agency clients: {response.status_code} - {response.text[:200]}")
                    return []
        except Exception as e:
            logger.debug(f"Error fetching VK agency clients (may not be agency): {e}")
            return []
    
    async def get_profiles(self) -> List[Dict[str, Any]]:
        """
        Получает список всех доступных профилей (аккаунтов) для выбора.
        Включает личный аккаунт и agency клиентов (если есть).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта/клиента
            - name: str - название
            - type: str - "personal" или "agency_client"
        """
        profiles = []
        seen_ids = set()
        
        # 1. Получаем личные аккаунты (кабинеты)
        try:
            accounts = await self.get_accounts()
            for account in accounts:
                account_id = account.get("id")
                if account_id and account_id not in seen_ids:
                    # Используем оригинальное название кабинета из API
                    account_name = account.get("name", f"Аккаунт {account_id}")
                    profiles.append({
                        "id": account_id,
                        "name": account_name,  # Показываем оригинальное название кабинета
                        "type": "personal"
                    })
                    seen_ids.add(account_id)
                    logger.info(f"✅ Added VK account: id={account_id}, name='{account_name}'")
        except Exception as e:
            logger.warning(f"Failed to fetch personal VK accounts: {e}")
        
        # 2. Получаем agency клиентов (если есть)
        try:
            agency_clients = await self.get_agency_clients()
            for client in agency_clients:
                client_id = client.get("id")
                if client_id and client_id not in seen_ids:
                    profiles.append({
                        "id": client_id,
                        "name": f"Клиент агентства ({client.get('name', client_id)})",
                        "type": "agency_client"
                    })
                    seen_ids.add(client_id)
                    logger.info(f"✅ Added VK agency client: {client_id}")
        except Exception as e:
            logger.debug(f"No agency clients found or error: {e}")
        
        # 3. Fallback: Если ничего не найдено, используем account_id из интеграции
        if not profiles and self.account_id:
            profiles.append({
                "id": str(self.account_id),
                "name": f"Аккаунт ({self.account_id})",
                "type": "personal"
            })
            logger.info(f"✅ Added fallback VK profile from account_id: {self.account_id}")
        
        # 4. Fallback: Если account_id не определен, пытаемся получить его из первой кампании
        if not profiles:
            try:
                campaigns = await self.get_campaigns()
                if campaigns:
                    # Попробуем извлечь account_id из данных кампании
                    # Для VK Ads, account_id может быть в данных кампании или мы используем токен по умолчанию
                    logger.info(f"⚠️ No profiles found, but {len(campaigns)} campaigns available. Using default account.")
                    profiles.append({
                        "id": "default",
                        "name": "Аккаунт по умолчанию",
                        "type": "personal"
                    })
            except Exception as e:
                logger.warning(f"Failed to get campaigns for fallback profile: {e}")
        
        # 5. Final fallback: Создаем профиль "default" если ничего не найдено
        if not profiles:
            logger.warning("⚠️ No VK profiles found, creating default profile")
            profiles.append({
                "id": "default",
                "name": "Аккаунт по умолчанию",
                "type": "personal"
            })
        
        return profiles
        
        # Fallback: если ничего не найдено, возвращаем текущий account_id если он есть
        if not profiles and self.account_id:
            profiles.append({
                "id": str(self.account_id),
                "name": f"Аккаунт ({self.account_id})",
                "type": "personal"
            })
            logger.info(f"✅ Added fallback VK account: {self.account_id}")
        
        return profiles
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        Получает баланс рекламного кабинета VK Ads.
        
        Returns:
            Dict с полями:
            - balance: float - баланс в валюте кабинета
            - currency: str - код валюты (RUB, USD, EUR, etc.)
            Или None при ошибке
        """
        # VK Ads API v2: получение информации об аккаунте
        # Используем ad_accounts.json для получения баланса (тот же эндпоинт, что и для списка аккаунтов)
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
                        # VK Ads API возвращает баланс в разных полях в зависимости от версии API
                        balance = account.get("balance") or account.get("amount") or account.get("funds")
                        currency = account.get("currency", "RUB")
                        
                        if balance is not None:
                            try:
                                balance_float = float(balance) if isinstance(balance, str) else balance
                                logger.info(f"VK Ads balance: {balance_float} {currency}")
                                return {
                                    "balance": balance_float,
                                    "currency": currency
                                }
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to parse VK balance value: {balance}, error: {e}")
                                return None
                else:
                    logger.warning(f"Failed to fetch VK Ads balance: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.warning(f"Error fetching VK Ads balance: {e}")
            return None