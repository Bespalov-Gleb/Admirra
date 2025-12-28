import httpx
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class YandexMetricaAPI:
    def __init__(self, access_token: str):
        self.base_url = "https://api-metrica.yandex.net/stat/v1/data"
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

    async def get_goals_stats(self, counter_id: str, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Fetches goal conversions from Yandex Metrica.
        """
        # To get specific goals, we first need to know goal IDs. 
        # For simplicity, we can fetch all goals conversions in one go using ym:s:goal<ID>reaches if we had IDs.
        # Here we just fetch general conversion rate as an example.
        params = {
            "ids": counter_id,
            "metrics": "ym:s:anyGoalConversionRate,ym:s:sumGoalReachesAny",
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
