import httpx
import json
import asyncio
from datetime import date, datetime
from typing import List, Dict, Any
import logging
from core.logging_utils import log_structured

logger = logging.getLogger(__name__)

class YandexDirectAPI:
    def __init__(self, access_token: str, client_login: str = None):
        """
        Initialize Yandex Direct API client.
        
        ARCHITECTURE: One token can have access to multiple advertising profiles.
        - Personal account: no Client-Login header needed
        - Agency/managed accounts: Client-Login header is REQUIRED to filter campaigns by profile
        """
        self.report_url = "https://api.direct.yandex.com/json/v5/reports"
        self.campaigns_url = "https://api.direct.yandex.com/json/v5/campaigns"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept-Language": "ru",
            "processingMode": "auto"
        }
        
        # Set Client-Login header if profile is specified
        # This is CRITICAL for filtering campaigns by selected profile
        self.client_login = client_login
        if client_login:
            self.headers["Client-Login"] = client_login
            logger.info(f"YandexDirectAPI initialized with Client-Login: {client_login}")
            log_structured('info', 'Yandex API initialized',
                         context={'has_client_login': True, 'client_login': client_login},
                         api_mode='agency_or_managed')
        else:
            logger.info("YandexDirectAPI initialized without Client-Login (personal account)")
            log_structured('info', 'Yandex API initialized',
                         context={'has_client_login': False},
                         api_mode='personal_token')
        
        # Track API Units usage
        self.units_used = 0
        self.units_limit = 0
        self.units_remaining = 0
    
    def _parse_and_check_units(self, units_header: str) -> None:
        """
        Parse Units header and check if we're approaching or exceeded limits.
        Format: "used/limit/remaining" (e.g., "120/10000/9880")
        """
        if not units_header:
            return
            
        try:
            parts = units_header.split('/')
            if len(parts) == 3:
                self.units_used = int(parts[0])
                self.units_limit = int(parts[1])
                self.units_remaining = int(parts[2])
                
                logger.info(f"Yandex API Units: {self.units_used}/{self.units_limit} (remaining: {self.units_remaining})")
                log_structured('info', 'API Units tracked',
                             context={'client_login': self.client_login},
                             units_used=self.units_used,
                             units_limit=self.units_limit,
                             units_remaining=self.units_remaining)
                
                # Warning if less than 10% remaining
                if self.units_limit > 0:
                    usage_percent = (self.units_used / self.units_limit) * 100
                    if usage_percent > 90:
                        logger.warning(f"API Units usage at {usage_percent:.1f}%! Consider slowing down requests.")
                    
                # Critical: Stop if limit exceeded
                if self.units_remaining <= 0:
                    raise RuntimeError(
                        f"Yandex API Units limit exceeded: {self.units_used}/{self.units_limit}. "
                        "Please wait for the limit to reset (usually at midnight Moscow time)."
                    )
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse Units header '{units_header}': {e}")

    async def get_campaigns(self) -> List[Dict[str, Any]]:
        """
        Fetches the list of all campaigns using the Campaigns service.
        """
        log_structured('info', 'Fetching Yandex campaigns',
                     context={'client_login': self.client_login},
                     endpoint='campaigns')
        
        # DEBUG: Log headers to verify Client-Login is set
        client_login_header = self.headers.get("Client-Login", "NOT SET")
        logger.info(f"YandexDirectAPI.get_campaigns: Client-Login header = '{client_login_header}'")
        logger.info(f"YandexDirectAPI.get_campaigns: Full headers (without token) = {[k for k in self.headers.keys() if k != 'Authorization']}")
        
        payload = {
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id", "Name", "Status"]
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # DEBUG: Log request details
                logger.info(f"🔵 Sending request to Yandex API:")
                logger.info(f"   URL: {self.campaigns_url}")
                logger.info(f"   Client-Login header value: {self.headers.get('Client-Login', 'NOT SET')}")
                logger.info(f"   All headers being sent: {self.headers}")
                logger.info(f"   Payload: {payload}")
                
                # Make request
                response = await client.post(self.campaigns_url, json=payload, headers=self.headers, timeout=30.0)
                
                # DEBUG: Log what was ACTUALLY sent (from httpx's perspective)
                if hasattr(response, 'request'):
                    logger.info(f"   📤 Request that was ACTUALLY sent:")
                    logger.info(f"      Method: {response.request.method}")
                    logger.info(f"      URL: {response.request.url}")
                    logger.info(f"      Headers: {dict(response.request.headers)}")
                    logger.info(f"      Client-Login in sent headers: {'Client-Login' in response.request.headers}")
                
                # DEBUG: Log response details
                logger.info(f"🟢 Received response from Yandex API:")
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # DEBUG: Log full response structure
                    logger.info(f"   Response keys: {list(data.keys())}")
                    
                    if "result" in data and "Campaigns" in data["result"]:
                        campaigns = data["result"]["Campaigns"]
                        logger.info(f"   🔴 CRITICAL: API returned {len(campaigns)} campaigns")
                        
                        # Log first 3 campaign names for debugging
                        for idx, c in enumerate(campaigns[:3]):
                            logger.info(f"      Campaign {idx + 1}: ID={c['Id']}, Name={c['Name']}, Status={c['Status']}")
                        
                        if len(campaigns) > 3:
                            logger.info(f"      ... and {len(campaigns) - 3} more campaigns")
                        
                        return [
                            {
                                "id": str(c["Id"]),
                                "name": c["Name"],
                                "status": c["Status"]
                            }
                            for c in campaigns
                        ]
                    elif "error" in data:
                        error_code = data["error"].get("error_code")
                        error_detail = data["error"].get("error_detail", "")
                        
                        # ERROR 3228: API доступен только в режиме Директ Про
                        # Fallback to Reports API which works for all accounts
                        if error_code == 3228:
                            logger.warning(f"⚠️ Campaigns.get API not available (error 3228: {error_detail}). Falling back to Reports API...")
                            return await self.get_campaigns_from_reports()
                        
                        error_msg = json.dumps(data["error"])
                        raise Exception(f"Yandex API Error: {error_msg}")
                
                raise Exception(f"Failed to fetch Yandex campaigns: {response.status_code} - {response.text}")
            except Exception as e:
                # Check if it's the 3228 error (already handled above, but just in case)
                if "error_code\":3228" in str(e) or "Директ Про" in str(e):
                    logger.warning(f"⚠️ Caught 3228 error in exception handler. Falling back to Reports API...")
                    return await self.get_campaigns_from_reports()
                
                logger.error(f"Error fetching Yandex campaigns: {e}")
                raise

    async def get_campaigns_from_reports(self) -> List[Dict[str, Any]]:
        """
        FALLBACK METHOD: Get campaigns list using Reports API.
        This works for ALL Yandex Direct accounts, including those in new interface.
        
        Uses a minimal date range to get campaign list without heavy data.
        """
        logger.info("📊 Getting campaigns list via Reports API (fallback method)")
        
        # Use yesterday's date for a lightweight report
        from datetime import datetime, timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "params": {
                "SelectionCriteria": {
                    "DateFrom": yesterday,
                    "DateTo": yesterday
                },
                "FieldNames": ["CampaignId", "CampaignName"],
                "ReportName": "Campaign List Report",
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "DateRangeType": "CUSTOM_DATE",
                "Format": "TSV",
                "IncludeVAT": "NO",
                "IncludeDiscount": "NO"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.report_url,
                json=payload,
                headers=self.headers,
                timeout=60.0
            )
            
            # Handle 201/202 (report is being generated)
            max_poll_attempts = 10
            poll_attempt = 0
            
            while response.status_code in [201, 202] and poll_attempt < max_poll_attempts:
                retry_in = int(response.headers.get("retryIn", 5))
                logger.info(f"   Report generating... retrying in {retry_in}s (attempt {poll_attempt + 1}/{max_poll_attempts})")
                
                await asyncio.sleep(retry_in)
                
                response = await client.post(
                    self.report_url,
                    json=payload,
                    headers=self.headers,
                    timeout=60.0
                )
                poll_attempt += 1
            
            if response.status_code == 200:
                # Parse TSV response
                tsv_data = response.text
                lines = tsv_data.strip().split('\n')
                
                if len(lines) < 2:  # No data (only header or empty)
                    logger.warning("Reports API returned no campaigns")
                    return []
                
                campaigns_dict = {}  # Use dict to deduplicate by ID
                
                # Skip header line and last line (totals)
                for line in lines[1:-1]:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        campaign_id = parts[0].strip()
                        campaign_name = parts[1].strip()
                        
                        if campaign_id and campaign_id != '--':
                            campaigns_dict[campaign_id] = {
                                "id": campaign_id,
                                "name": campaign_name,
                                "status": "UNKNOWN"  # Reports API doesn't return status
                            }
                
                campaigns_list = list(campaigns_dict.values())
                logger.info(f"✅ Reports API returned {len(campaigns_list)} unique campaigns")
                return campaigns_list
            
            elif response.status_code == 400:
                error_data = response.text
                logger.error(f"Reports API error 400: {error_data}")
                
                # If even Reports API fails, return empty list
                logger.warning("Reports API also failed. Returning empty campaign list.")
                return []
            
            else:
                logger.error(f"Reports API error {response.status_code}: {response.text}")
                return []
    
    async def get_report(self, date_from: str, date_to: str, level: str = "campaign", max_retries: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches a report from Yandex Direct API v5.
        Handles polling for 201/202 statuses and tracks API units.
        """
        # VALIDATION: Date format and range
        try:
            from datetime import datetime as dt
            dt_from = dt.strptime(date_from, "%Y-%m-%d")
            dt_to = dt.strptime(date_to, "%Y-%m-%d")
            
            if dt_from > dt_to:
                raise ValueError(f"date_from ({date_from}) cannot be after date_to ({date_to})")
            
            # Yandex Direct has limits on date range (usually 90-180 days)
            date_range_days = (dt_to - dt_from).days
            if date_range_days > 365:
                logger.warning(f"Date range is {date_range_days} days, which may be too large for Yandex API")
                
        except ValueError as e:
            raise ValueError(f"Invalid date format. Expected YYYY-MM-DD: {e}")
        
        field_names = ["Date", "CampaignId", "CampaignName", "Impressions", "Clicks", "Cost", "Conversions"]
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
                    self.report_url,
                    json=report_definition,
                    headers=self.headers,
                    timeout=60.0
                )

                # Track and validate API Units (Points)
                units = response.headers.get("Units")
                if units:
                    self._parse_and_check_units(units)

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
                    # Handle specific error codes
                    error_msg = f"Yandex Direct API Error: {response.status_code}"
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error_msg += f" - {error_data['error'].get('error_string', error_data['error'])}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    
                    logger.error(error_msg)
                    
                    # Raise specific exceptions for different error codes
                    if response.status_code == 400:
                        raise ValueError(f"Bad request to Yandex API: {error_msg}")
                    elif response.status_code == 401:
                        raise PermissionError(f"Unauthorized access to Yandex API: {error_msg}")
                    elif response.status_code == 403:
                        raise PermissionError(f"Forbidden access to Yandex API: {error_msg}")
                    else:
                        raise Exception(error_msg)

            # Max retries reached
            raise TimeoutError(f"Maximum retries ({max_retries}) reached for Yandex report generation. Report may be too large or API is overloaded.")

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
                        if len(cols) >= 8: # These reports have 8 columns
                            results.append({
                                "date": cols[0],
                                "campaign_name": cols[3], # Index 3 is CampaignName
                                "name": cols[2], # Index 2 is AdGroupName or Criteria
                                "impressions": int(cols[4]) if cols[4].isdigit() else 0,
                                "clicks": int(cols[5]) if cols[5].isdigit() else 0,
                                "cost": float(cols[6]) / 1000000 if cols[6].replace('.', '', 1).isdigit() else 0.0,
                                "conversions": int(cols[7]) if cols[7].isdigit() else 0
                            })
                    else:
                        if len(cols) >= 7:
                            results.append({
                                "date": cols[0],
                                "campaign_id": cols[1],
                                "campaign_name": cols[2],
                                "impressions": int(cols[3]) if cols[3].isdigit() else 0,
                                "clicks": int(cols[4]) if cols[4].isdigit() else 0,
                                "cost": float(cols[5]) / 1000000 if cols[5].replace('.', '', 1).isdigit() else 0.0,
                                "conversions": int(cols[6]) if cols[6].isdigit() else 0
                            })
                except (ValueError, IndexError):
                    continue
        return results

    async def get_clients(self) -> List[Dict[str, Any]]:
        """
        Fetches information about the current client, including ManagedLogins for shared access.
        """
        url = "https://api.direct.yandex.com/json/v5/clients"
        payload = {
            "method": "get",
            "params": {
                "FieldNames": ["Login", "ClientInfo", "ManagedLogins"]
            }
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data and "Clients" in data["result"]:
                        return data["result"]["Clients"]
                    elif "error" in data:
                        error_msg = f"Yandex Clients API Error: {data['error']}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    else:
                        raise Exception(f"Unexpected response format from Yandex Clients API: {data}")
                else:
                    error_msg = f"Failed to fetch Yandex clients: {response.status_code} - {response.text[:200]}"
                    logger.error(error_msg)
                    if response.status_code == 401:
                        raise PermissionError(f"Unauthorized: {error_msg}")
                    elif response.status_code == 403:
                        raise PermissionError(f"Forbidden: {error_msg}")
                    else:
                        raise Exception(error_msg)
            except Exception as e:
                logger.error(f"Failed to fetch Yandex clients: {e}")
                raise
