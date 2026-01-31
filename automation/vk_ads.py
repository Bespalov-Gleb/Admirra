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
        Получает список всех рекламных кампаний (AdPlans).
        
        Согласно документации VK Ads API:
        Endpoint: GET /api/v2/ad_plans.json
        Параметры:
        - client_id (опционально) - ID кабинета для фильтрации кампаний
        
        Returns:
            List[Dict] с полями:
            - id: str - ID кампании
            - name: str - название кампании
            - status: str - статус кампании
        """
        url = f"{self.base_url}/ad_plans.json"
        params = {}
        
        # Согласно документации, client_id используется для фильтрации кампаний по кабинету
        if self.account_id:
            params["client_id"] = self.account_id
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 Retrieved {len(items)} campaign(s) from VK Ads API")
                    
                    return [
                        {
                            "id": str(item["id"]),
                            "name": item["name"],
                            "status": item.get("status")
                        }
                        for item in items
                    ]
                else:
                    error_text = response.text[:200] if response.text else "No error message"
                    raise Exception(f"Failed to fetch VK campaigns: {response.status_code} - {error_text}")
        except Exception as e:
            logger.error(f"Error fetching VK campaigns: {e}")
            raise e

    async def get_statistics(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Получает статистику по рекламным кампаниям (AdPlans).
        
        Согласно документации VK Ads API (https://ads.vk.com/doc/api/info/Statistics):
        Endpoint: GET /api/v2/statistics/ad_plans/day.json
        Параметры:
        - date_from (обязательно) - начальная дата (YYYY-MM-DD)
        - date_to (обязательно) - конечная дата (YYYY-MM-DD)
        - metrics (по умолчанию "base") - набор метрик
        - id (опционально) - список ID кампаний для фильтрации
        - client_id (опционально) - ID кабинета для фильтрации
        
        Автоматически разбивает диапазон дат на чанки по 90 дней для соблюдения лимитов API.
        """
        # Получаем названия кампаний для маппинга
        campaigns = await self.get_campaigns()
        names_map = {int(c["id"]): c["name"] for c in campaigns}
        
        # Разбиваем диапазон дат на чанки (максимум 366 дней согласно документации)
        date_chunks = self._split_date_range(date_from, date_to, 90)
        all_results = []

        async with httpx.AsyncClient() as client:
            for d_from, d_to in date_chunks:
                # Согласно документации: GET /api/v2/statistics/ad_plans/day.json
                url = f"{self.base_url}/statistics/ad_plans/day.json"
                params = {
                    "date_from": d_from,
                    "date_to": d_to,
                    "metrics": "base"  # Базовые метрики: shows, clicks, spent, cpm, cpc, ctr, vk.goals, vk.cpa, vk.cr
                }
                
                # Параметр client_id используется для фильтрации статистики по кабинету
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
                        # Согласно документации, 400 может быть для:
                        # - ERR_WRONG_PARAMETER - некорректное значение параметра
                        # - ERR_LIMIT_EXCEEDED - превышен лимит запрашиваемых дат или количества объектов
                        # - ERR_WRONG_DATE - некорректная дата
                        logger.warning(f"VK Ads API returned 400 for range {d_from}-{d_to}. Likely old data or invalid params. Response: {response.text[:200]}")
                    else:
                        logger.error(f"VK Ads API error for range {d_from}-{d_to}: {response.status_code} - {response.text[:200]}")
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
        Парсит ответ VK Ads API Statistics.
        
        Согласно документации (https://ads.vk.com/doc/api/info/Statistics):
        Структура ответа:
        {
          "items": [
            {
              "id": <campaign_id>,
              "rows": [
                {
                  "date": "YYYY-MM-DD",
                  "base": {
                    "shows": <impressions>,
                    "clicks": <clicks>,
                    "spent": <cost>,
                    "vk.goals": <conversions>,
                    "vk.cpa": <cpa>,
                    "vk.cr": <conversion_rate>
                  }
                }
              ]
            }
          ]
        }
        """
        results = []
        items = data.get("items", [])
        for item in items:
            campaign_id = item.get("id")
            campaign_name = names_map.get(campaign_id, f"Campaign {campaign_id}")
            rows = item.get("rows", [])
            for row in rows:
                base = row.get("base", {})
                # Дата находится на уровне row
                row_date = row.get("date")
                if not row_date:
                    continue
                
                # Согласно документации, метрики в base:
                # - shows - количество показов
                # - clicks - количество кликов
                # - spent - списания
                # - vk.goals - количество достижений целей
                # - vk.cpa - среднее списание за достижение 1 цели
                # - vk.cr - процентное отношение количества достижений целей к количеству кликов
                results.append({
                    "date": row_date,
                    "campaign_id": str(campaign_id) if campaign_id else "",
                    "campaign_name": campaign_name,
                    "impressions": int(base.get("shows", 0)),
                    "clicks": int(base.get("clicks", 0)),
                    "cost": float(base.get("spent", 0)),
                    "conversions": int(base.get("vk.goals", 0))  # Используем vk.goals согласно документации
                })
        return results
    
    async def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных рекламных аккаунтов (кабинетов).
        
        Согласно документации VK Ads API (https://ads.vk.com/doc/api/info/Statistics):
        Используем endpoint /api/v2/statistics/users/summary.json без параметра id
        для получения списка всех доступных кабинетов (users).
        
        Returns:
            List[Dict] с полями:
            - id: str - ID аккаунта (нормализованный числовой ID)
            - name: str - название аккаунта
            - status: str - статус аккаунта
        """
        accounts = []
        
        # Метод 1: Используем Statistics API для получения списка кабинетов
        # Документация: https://ads.vk.com/doc/api/info/Statistics
        # GET /api/v2/statistics/users/summary.json (без параметра id возвращает все кабинеты)
        try:
            url = f"{self.base_url}/statistics/users/summary.json"
            params = {
                "metrics": "base"  # Базовые метрики для получения списка кабинетов
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 VK Ads Statistics API returned {len(items)} account(s) from users/summary.json")
                    
                    for item in items:
                        raw_id = item.get("id")
                        if not raw_id:
                            continue
                            
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
                            # Пытаемся получить название кабинета из статистики или используем ID
                            account_name = f"Кабинет {account_id}"  # По умолчанию
                            
                            # Если есть данные в статистике, можно попытаться извлечь название
                            # Но обычно название нужно получать из другого endpoint
                            
                            accounts.append({
                                "id": account_id,
                                "name": account_name,
                                "status": "active"
                            })
                            
                            logger.info(f"✅ Added VK account from statistics: id={account_id}")
                        else:
                            logger.warning(f"⚠️ Could not extract numeric ID from: '{raw_id_str}', skipping")
                    
                    if accounts:
                        logger.info(f"✅ Successfully retrieved {len(accounts)} VK account(s) via Statistics API")
                        # Пытаемся получить названия кабинетов из кампаний
                        await self._enrich_accounts_with_names(accounts)
                        return accounts
                else:
                    logger.warning(f"⚠️ VK Ads Statistics API returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching VK accounts from Statistics API: {e}")
        
        # Метод 2: Fallback - пытаемся использовать старый endpoint
        try:
            url = f"{self.base_url}/ad_accounts.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📋 VK Ads API returned {len(items)} account(s) from ad_accounts.json (fallback)")
                    
                    for item in items:
                        raw_id = item.get("id")
                        raw_id_str = str(raw_id)
                        
                        import re
                        account_id = None
                        
                        if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                            match = re.search(r'vkads_(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        elif raw_id_str.isdigit():
                            account_id = raw_id_str
                        else:
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
                            
                            logger.info(f"✅ Added VK account: id={account_id}, name='{account_name}'")
                    
                    if accounts:
                        logger.info(f"✅ Successfully retrieved {len(accounts)} VK account(s) via fallback method")
                        return accounts
        except Exception as e:
            logger.debug(f"Fallback method failed: {e}")
        
        # Метод 3: Извлекаем из статистики кампаний
        try:
            accounts = await self._get_accounts_from_statistics()
            if accounts:
                logger.info(f"✅ Found {len(accounts)} account(s) via statistics extraction method")
                return accounts
        except Exception as e:
            logger.debug(f"Statistics extraction method failed: {e}")
        
        # Fallback: Если account_id задан в конструкторе, используем его
        if self.account_id:
            account_id_str = str(self.account_id)
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
    
    async def _enrich_accounts_with_names(self, accounts: List[Dict[str, Any]]):
        """
        Обогащает список кабинетов названиями, получая их из кампаний.
        Для каждого кабинета запрашиваем первую кампанию и пытаемся извлечь название.
        """
        try:
            async with httpx.AsyncClient() as client:
                for account in accounts:
                    account_id = account.get("id")
                    if not account_id:
                        continue
                    
                    # Запрашиваем кампании для этого кабинета
                    # Согласно документации, можно использовать client_id для фильтрации
                    try:
                        campaigns_url = f"{self.base_url}/ad_plans.json"
                        campaigns_params = {"client_id": account_id, "limit": 1}
                        campaigns_response = await client.get(
                            campaigns_url,
                            params=campaigns_params,
                            headers=self.headers,
                            timeout=10.0
                        )
                        
                        if campaigns_response.status_code == 200:
                            campaigns_data = campaigns_response.json()
                            campaigns_items = campaigns_data.get("items", [])
                            # Если есть кампании, можно использовать их для определения названия кабинета
                            # Но обычно название кабинета не содержится в данных кампаний
                            pass
                    except Exception as e:
                        logger.debug(f"Could not enrich account {account_id} with name: {e}")
        except Exception as e:
            logger.debug(f"Error enriching accounts with names: {e}")
    
    async def _get_accounts_from_statistics(self) -> List[Dict[str, Any]]:
        """
        Альтернативный метод получения кабинетов: используем статистику по users.
        
        Согласно документации VK Ads API:
        GET /api/v2/statistics/users/day.json или summary.json
        Без параметра id возвращает статистику по всем доступным кабинетам.
        """
        accounts = []
        seen_ids = set()
        
        try:
            from datetime import datetime, timedelta
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # Используем статистику по users (кабинетам) для получения списка
            # Согласно документации: GET /api/v2/statistics/users/day.json
            url = f"{self.base_url}/statistics/users/day.json"
            params = {
                "date_from": date_from,
                "date_to": date_to,
                "metrics": "base"  # Базовые метрики
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    logger.info(f"📊 Statistics/users response contains {len(items)} account(s)")
                    
                    # Извлекаем уникальные ID кабинетов из статистики
                    for item in items:
                        raw_id = item.get("id")
                        if not raw_id:
                            continue
                            
                        raw_id_str = str(raw_id)
                        
                        # Нормализуем account_id
                        import re
                        account_id = None
                        
                        if '@vk@' in raw_id_str or raw_id_str.startswith('vkads_'):
                            match = re.search(r'vkads_(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                            else:
                                match = re.search(r'(\d+)', raw_id_str)
                                if match:
                                    account_id = match.group(1)
                        elif raw_id_str.isdigit():
                            account_id = raw_id_str
                        else:
                            match = re.search(r'(\d+)', raw_id_str)
                            if match:
                                account_id = match.group(1)
                        
                        if account_id and account_id not in seen_ids:
                            seen_ids.add(account_id)
                            
                            accounts.append({
                                "id": account_id,
                                "name": f"Кабинет {account_id}",
                                "status": "active"
                            })
                            
                            logger.info(f"✅ Extracted account from users statistics: id={account_id}")
                    
                    if accounts:
                        logger.info(f"✅ Extracted {len(accounts)} unique account(s) from users statistics")
                else:
                    logger.warning(f"⚠️ Statistics/users request returned {response.status_code}: {response.text[:200]}")
                    
        except Exception as e:
            logger.error(f"❌ Error extracting accounts from users statistics: {e}")
        
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