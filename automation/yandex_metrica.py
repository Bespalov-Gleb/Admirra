import httpx
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class YandexMetricaAPI:
    def __init__(self, access_token: str, client_login: str = None):
        self.base_url = "https://api-metrica.yandex.net/stat/v1/data"
        self.client_login = client_login
        self.headers = {
            "Authorization": f"OAuth {access_token}"
        }

    async def get_stats(self, counter_id: str, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Fetches statistics from Yandex Metrica API.
        """
        params = {
            "ids": counter_id,
            "metrics": "ym:s:visits,ym:s:users,ym:s:pageviews",
            "dimensions": "ym:s:date",
            "date1": date_from,
            "date2": date_to,
            "group": "day",
            "sort": "ym:s:date"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                results = []
                for row in data.get('data', []):
                    results.append({
                        "date": row['dimensions'][0]['name'],
                        "visits": row['metrics'][0],
                        "users": row['metrics'][1],
                        "pageviews": row['metrics'][2]
                    })
                return results
            else:
                logger.error(f"Yandex Metrica API Error: {response.status_code} - {response.text}")
                return []

    async def get_goals_stats(self, counter_id: str, date_from: str, date_to: str, metrics: str = "ym:s:anyGoalConversionRate,ym:s:sumGoalVisitsAny", filter_by_direct: bool = True) -> List[Dict[str, Any]]:
        """
        Fetches goal visits (целевые визиты) from Yandex Metrica.
        CRITICAL: Uses visits instead of reaches to get target visits, not goal achievements.
        
        Args:
            counter_id: ID счетчика Метрики
            date_from: Начальная дата (YYYY-MM-DD)
            date_to: Конечная дата (YYYY-MM-DD)
            metrics: Метрики для запроса
            filter_by_direct: Если True, фильтрует данные только по Яндекс.Директ и Яндекс.Директ (неопределено)
        
        Согласно документации Яндекс.Метрики API:
        - Параметр `filters` используется для фильтрации данных
        - `ym:s:lastSignAdvEngine` - последняя рекламная система
        - Значения: 'Yandex Direct' и 'Yandex Direct (undefined)'
        """
        params = {
            "ids": counter_id,
            "metrics": metrics,
            "dimensions": "ym:s:date",
            "date1": date_from,
            "date2": date_to
        }
        
        # CRITICAL: Фильтруем данные только по Яндекс.Директ и Яндекс.Директ (неопределено)
        # Согласно документации Яндекс.Метрики API:
        # - Параметр filters использует синтаксис: "ym:s:lastSignAdvEngine=='Yandex Direct'"
        # - Для нескольких значений используется оператор OR
        # - Значения: 'Yandex Direct' и 'Yandex Direct (undefined)'
        # - Важно: значения должны быть в одинарных кавычках
        if filter_by_direct:
            # Фильтр для Яндекс.Директ и Яндекс.Директ (неопределено)
            # Используем оператор OR для включения обоих значений
            # Формат согласно документации: "ym:s:lastSignAdvEngine=='Yandex Direct' OR ym:s:lastSignAdvEngine=='Yandex Direct (undefined)'"
            filters = "ym:s:lastSignAdvEngine=='Yandex Direct' OR ym:s:lastSignAdvEngine=='Yandex Direct (undefined)'"
            params["filters"] = filters
            logger.info(f"📊 Applying Yandex Direct filter to Metrika goals query: {filters}")

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            elif response.status_code == 429:
                # Raise exception with status_code for queue to handle
                error = Exception(f"429 Too Many Requests")
                error.status_code = 429
                error.response = response
                raise error
            else:
                logger.warning(f"Yandex Metrica API error {response.status_code}: {response.text[:200]}")
                return []

    async def get_counters(self) -> List[Dict[str, Any]]:
        """
        Lists all accessible counters.
        CRITICAL: If client_login is provided, API should filter counters by that profile.
        However, API may return all accessible counters regardless of ulogin parameter.
        We rely on backend filtering by owner_login after fetching.
        """
        url = "https://api-metrica.yandex.net/management/v1/counters"
        params = {}
        if self.client_login:
            params["ulogin"] = self.client_login
            logger.info(f"📊 YandexMetricaAPI.get_counters: Using ulogin={self.client_login} to filter counters")
        else:
            logger.info(f"📊 YandexMetricaAPI.get_counters: No client_login, fetching all accessible counters")
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                counters = data.get('counters', [])
                logger.info(f"📊 YandexMetricaAPI.get_counters: API returned {len(counters)} counters")
                if self.client_login:
                    # Log owner_login for each counter to verify filtering
                    for counter in counters:
                        owner_login = counter.get('owner_login', 'N/A')
                        logger.debug(f"   Counter '{counter.get('name')}' (ID: {counter.get('id')}): owner_login={owner_login}")
                return counters
            
            error_msg = f"Failed to fetch counters: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def get_counter_goals(self, counter_id: str) -> List[Dict[str, Any]]:
        """
        Lists all goals for a specific counter.
        """
        url = f"https://api-metrica.yandex.net/management/v1/counter/{counter_id}/goals"
        params = {}
        if self.client_login:
            params["ulogin"] = self.client_login
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('goals', [])
            
            error_msg = f"Failed to fetch goals for counter {counter_id}: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    @staticmethod
    def normalize_domain(url: str) -> str:
        """
        Extract and normalize domain from Metrika counter site URL.
        Returns normalized domain (e.g., 'kxi-stroi.rf' from 'https://www.kxi-stroi.rf/').
        """
        if not url:
            return ""
        # Remove protocol
        url = url.replace("http://", "").replace("https://", "")
        # Remove www.
        if url.startswith("www."):
            url = url[4:]
        # Remove path and query
        url = url.split("/")[0].split("?")[0]
        # Remove port
        url = url.split(":")[0]
        # Lowercase
        return url.lower().strip()
