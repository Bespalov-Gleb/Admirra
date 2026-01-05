import httpx
import json
import asyncio
from datetime import date, datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class YandexDirectAPI:
    def __init__(self, access_token: str, client_login: str = None):
        self.url = "https://api.direct.yandex.com/json/v5/reports"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept-Language": "ru",
            "processingMode": "auto"
        }
        # AGENCY MODE: Inject Client-Login header if provided
        if client_login:
            self.headers["Client-Login"] = client_login
            logger.info(f"Initialized Yandex API with Agency Client-Login: {client_login}")

    async def get_report(self, date_from: str, date_to: str, level: str = "campaign", max_retries: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches a report from Yandex Direct API v5.
        Handles polling for 201/202 statuses and tracks API units.
        """
        field_names = ["Date", "CampaignName", "Impressions", "Clicks", "Cost", "Conversions"]
        if level == "keyword":
            field_names.insert(2, "Criteria")
            report_type = "CRITERIA_PERFORMANCE_REPORT"
        elif level == "group":
            field_names.insert(2, "AdGroupName")
            report_type = "ADGROUP_PERFORMANCE_REPORT"
        else:
            report_type = "CAMPAIGN_PERFORMANCE_REPORT"

        report_definition = {
            "params": {
                "SelectionCriteria": {
                    "DateFrom": date_from,
                    "DateTo": date_to
                },
                "FieldNames": field_names,
                "ReportName": f"AgencyStats_{level}_{date_from}_{date_to}_{int(datetime.now().timestamp())}",
                "ReportType": report_type,
                "DateRangeType": "CUSTOM_DATE",
                "Format": "TSV",
                "IncludeVAT": "NO"
            }
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                response = await client.post(
                    self.url,
                    json=report_definition,
                    headers=self.headers,
                    timeout=60.0
                )

                # Track API Units (Points)
                units = response.headers.get("Units")
                if units:
                    # Format: used/limit/remaining
                    logger.info(f"Yandex API Units: {units}")

                if response.status_code == 200:
                    return self._parse_tsv(response.text, level)
                
                elif response.status_code in [201, 202]:
                    # Report is being generated or in queue
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.info(f"Report is in progress (Status {response.status_code}). Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    # Loop continues to retry
                    
                elif response.status_code == 429:
                    # Too Many Requests
                    logger.warning("Yandex API Rate Limit (429) hit. Waiting 10 seconds...")
                    await asyncio.sleep(10)
                    
                elif response.status_code >= 500:
                    # Server error
                    logger.error(f"Yandex Server Error ({response.status_code}). Retrying in 5s...")
                    await asyncio.sleep(5)
                
                else:
                    logger.error(f"Yandex Direct API Error: {response.status_code} - {response.text}")
                    return []

            logger.error("Maximum retries reached for Yandex report generation.")
            return []

    def _parse_tsv(self, tsv_data: str, level: str = "campaign") -> List[Dict[str, Any]]:
        lines = tsv_data.strip().split('\n')
        if not lines:
            return []
        
        results = []
        for line in lines:
            if not line.strip():
                continue
                
            cols = line.split('\t')
            
            # Skip header or summary lines
            if cols[0] in ["Date", "Total", "Total rows:"] or "Total" in cols[0]:
                continue
            
            # Additional check: first column should look like a date (YYYY-MM-DD)
            if len(cols[0]) == 10 and cols[0][4] == '-' and cols[0][7] == '-':
                try:
                    if level in ["keyword", "group"]:
                        if len(cols) >= 7:
                            results.append({
                                "date": cols[0],
                                "campaign_name": cols[1],
                                "name": cols[2], # AdGroupName or Criteria
                                "impressions": int(cols[3]) if cols[3].isdigit() else 0,
                                "clicks": int(cols[4]) if cols[4].isdigit() else 0,
                                "cost": float(cols[5]) / 1000000 if cols[5].replace('.', '', 1).isdigit() else 0.0,
                                "conversions": int(cols[6]) if cols[6].isdigit() else 0
                            })
                    else:
                        if len(cols) >= 6:
                            results.append({
                                "date": cols[0],
                                "campaign_name": cols[1],
                                "impressions": int(cols[2]) if cols[2].isdigit() else 0,
                                "clicks": int(cols[3]) if cols[3].isdigit() else 0,
                                "cost": float(cols[4]) / 1000000 if cols[4].replace('.', '', 1).isdigit() else 0.0,
                                "conversions": int(cols[5]) if cols[5].isdigit() else 0
                            })
                except (ValueError, IndexError):
                    continue
        return results
