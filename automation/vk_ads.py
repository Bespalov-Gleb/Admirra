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

    async def _get_campaign_names(self) -> Dict[int, str]:
        """
        Fetches the list of campaigns (AdPlans) to map IDs to names.
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
                    return {item['id']: item['name'] for item in data.get('items', [])}
                else:
                    logger.error(f"Failed to fetch VK campaign names: {response.status_code}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching VK campaign names: {e}")
            return {}

    async def get_statistics(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        """
        Fetches statistics and maps campaign IDs to names.
        """
        # Fetch names first
        names_map = await self._get_campaign_names()
        
        url = f"{self.base_url}/statistics/campaigns/day.json"
        params = {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": "base"
        }
        if self.account_id:
            params["client_id"] = self.account_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers)
                if response.status_code == 200:
                    return self._parse_response(response.json(), names_map)
                else:
                    logger.error(f"VK Ads API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"VK Ads API Exception: {e}")
            return []

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
                    "campaign_name": campaign_name,
                    "impressions": int(base.get("shows", 0)),
                    "clicks": int(base.get("clicks", 0)),
                    "cost": float(base.get("spent", 0)),
                    "conversions": int(base.get("goals", 0))
                })
        return results
