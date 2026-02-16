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

    async def get_goals_stats(self, counter_id: str, date_from: str, date_to: str, metrics: str = "ym:s:anyGoalConversionRate,ym:s:sumGoalVisitsAny", goal_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetches goal visits (целевые визиты) from Yandex Metrica.
        Uses visits instead of reaches to get target visits, not goal achievements.
        Returns all conversions regardless of traffic source.
        """
        params = {
            "ids": counter_id,
            "metrics": metrics,
            "dimensions": "ym:s:datePeriod",
            "date1": date_from,
            "date2": date_to,
            "group": "day",
            "sort": "ym:s:date"
        }
        if goal_id:
            params["goal_id"] = goal_id

        logger.info(f"📊 Metrika Stat API: GET stat/v1/data counter={counter_id} date1={date_from} date2={date_to}")
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                # API может возвращать данные в разных форматах (v1 vs OpenAPI)
                rows = data.get('data', [])
                if not rows and isinstance(data.get('data'), dict):
                    rows = data['data'].get('data', data['data'].get('rows', []))
                if not rows and data.get('totals'):
                    totals = data.get('totals', [])
                    rows = [{'dimensions': [{'name': date_from}], 'metrics': totals}]
                # OpenAPI: каждая строка — [dimensions, metrics] вместо {dimensions, metrics}
                if rows and isinstance(rows[0], (list, tuple)):
                    converted = []
                    for r in rows:
                        dims, mets = (r[0], r[1]) if len(r) >= 2 else (r, [])
                        dim_objs = dims if isinstance(dims, list) and dims and isinstance(dims[0], dict) else [{'name': str(dims[0]) if dims else date_from}]
                        met_vals = mets if isinstance(mets, (list, tuple)) else [mets]
                        converted.append({'dimensions': dim_objs, 'metrics': met_vals})
                    rows = converted
                if not rows:
                    # Логируем структуру ответа для отладки (API может менять формат)
                    keys = list(data.keys()) if data else []
                    logger.warning(f"📊 Metrika Stat API: 0 rows. Response keys: {keys}")
                    for k in ['data', 'totals', 'Data', 'Totals', 'rows', 'Rows']:
                        if k in data and data[k]:
                            v = data[k]
                            logger.warning(f"📊   {k}={type(v).__name__} len={len(v) if hasattr(v, '__len__') else 'N/A'}")
                else:
                    logger.info(f"📊 Metrika Stat API: received {len(rows)} rows")
                return rows
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
