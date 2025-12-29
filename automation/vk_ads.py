import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

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
        Automatically splits date ranges into 90-day chunks to satisfy VK API limits.
        """
        # Fetch names first
        names_map = await self._get_campaign_names()
        
        # Split dates into chunks
        date_chunks = self._split_date_range(date_from, date_to, 90)
        all_results = []

        async with httpx.AsyncClient() as client:
            for d_from, d_to in date_chunks:
                url = f"{self.base_url}/statistics/campaigns/day.json"
                params = {
                    "date_from": d_from,
                    "date_to": d_to,
                    "metrics": "base"
                }
                if self.account_id:
                    params["client_id"] = self.account_id

                try:
                    response = await client.get(url, params=params, headers=self.headers)
                    if response.status_code == 200:
                        chunk_data = self._parse_response(response.json(), names_map)
                        all_results.extend(chunk_data)
                    else:
                        logger.error(f"VK Ads API error for range {d_from}-{d_to}: {response.status_code} - {response.text}")
                except Exception as e:
                    logger.error(f"VK Ads API Exception for range {d_from}-{d_to}: {e}")
                    
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
                    "campaign_name": campaign_name,
                    "impressions": int(base.get("shows", 0)),
                    "clicks": int(base.get("clicks", 0)),
                    "cost": float(base.get("spent", 0)),
                    "conversions": int(base.get("goals", 0))
                })
        return results
