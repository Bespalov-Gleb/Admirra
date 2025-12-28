import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class VKAdsAPI:
    def __init__(self, access_token: str, account_id: str = None):
        self.base_url = "https://ads.vk.com/api/v2" # Example base URL
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
        self.account_id = account_id

    async def get_statistics(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Fetches statistics from VK Ads API.
        Documentation: https://ads.vk.com/help/articles/api-stats
        """
        url = f"{self.base_url}/statistics/campaigns/day.json"
        
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": "base" # base includes impressions, clicks, spent
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers)
                if response.status_code == 200:
                    return self._parse_response(response.json())
                else:
                    logger.error(f"VK Ads API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"VK Ads API Exception: {e}")
            return []

    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses VK API JSON response.
        Structure: { "items": [ { "id": campaign_id, "rows": [ { "date": "...", "base": { "shows": 10, "clicks": 2, "spent": "1.50" } } ] } ] }
        """
        results = []
        items = data.get("items", [])
        for item in items:
            campaign_id = item.get("id")
            rows = item.get("rows", [])
            for row in rows:
                base = row.get("base", {})
                results.append({
                    "date": row.get("date"),
                    "campaign_name": f"Campaign {campaign_id}", # VK doesn't always return names in stats, usually just IDs
                    "impressions": int(base.get("shows", 0)),
                    "clicks": int(base.get("clicks", 0)),
                    "cost": float(base.get("spent", 0)),
                    "conversions": int(base.get("goals", 0)) # VK uses goals for conversions
                })
        return results
