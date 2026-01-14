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

    async def get_goals_stats(self, counter_id: str, date_from: str, date_to: str, metrics: str = "ym:s:anyGoalConversionRate,ym:s:sumGoalReachesAny") -> List[Dict[str, Any]]:
        """
        Fetches goal conversions from Yandex Metrica.
        """
        params = {
            "ids": counter_id,
            "metrics": metrics,
            "dimensions": "ym:s:date",
            "date1": date_from,
            "date2": date_to
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            return []

    async def get_counters(self) -> List[Dict[str, Any]]:
        """
        Lists all accessible counters.
        """
        url = "https://api-metrica.yandex.net/management/v1/counters"
        params = {}
        if self.client_login:
            params["ulogin"] = self.client_login
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('counters', [])
            
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
