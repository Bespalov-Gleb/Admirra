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
        # IMPORTANT: Client-Login must be the exact advertising account login (username), not email
        self.client_login = client_login
        if client_login:
            # Strip whitespace and ensure it's a string
            client_login_clean = str(client_login).strip()
            if client_login_clean:
                self.headers["Client-Login"] = client_login_clean
                logger.info(f"YandexDirectAPI initialized with Client-Login: '{client_login_clean}'")
                log_structured('info', 'Yandex API initialized',
                             context={'has_client_login': True, 'client_login': client_login_clean},
                             api_mode='agency_or_managed')
            else:
                logger.warning(f"YandexDirectAPI: client_login provided but empty after stripping: '{client_login}'")
                self.client_login = None
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
        
        # CRITICAL: Request ALL campaigns in ALL states INCLUDING ARCHIVED
        # According to Yandex Direct API docs:
        # - If States is not specified, returns all campaigns except CONVERTED
        # - We need ALL campaigns (including archived, awaiting payment, stopped, suspended, etc.)
        # - Explicitly include ARCHIVED to get archived campaigns for filtering
        selection_criteria = {
            "States": ["ON", "OFF", "SUSPENDED", "ENDED", "CONVERTED", "ARCHIVED"]  # Include ALL states including ARCHIVED
        }
        
        payload = {
            "method": "get",
            "params": {
                "SelectionCriteria": selection_criteria,
                "FieldNames": ["Id", "Name", "Status", "State", "StatusPayment", "Type"]  # Added Type for campaign type filtering
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
                    # Log headers but mask Authorization token
                    sent_headers = dict(response.request.headers)
                    if 'Authorization' in sent_headers:
                        sent_headers['Authorization'] = 'Bearer [REDACTED]'
                    logger.info(f"      Headers: {sent_headers}")
                    client_login_value = response.request.headers.get('Client-Login', 'NOT SET')
                    logger.info(f"      Client-Login header value: '{client_login_value}'")
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
                        logger.info(f"   🔴 Client-Login used: '{self.client_login}'")
                        logger.info(f"   🔴 Requested States: {selection_criteria.get('States', 'ALL')}")
                        
                        # Log ALL campaign names and IDs for debugging
                        logger.info(f"   🔴 ALL campaigns returned by API:")
                        archived_found = 0
                        for idx, c in enumerate(campaigns):
                            campaign_state = c.get('State', 'N/A')
                            status_payment = c.get('StatusPayment', 'N/A')
                            logger.info(f"      [{idx+1}] ID={c['Id']}, Name='{c['Name']}', Status={c['Status']}, State={campaign_state}, StatusPayment={status_payment}")
                            if campaign_state == 'ARCHIVED':
                                archived_found += 1
                        
                        if archived_found > 0:
                            logger.info(f"   📋 Found {archived_found} ARCHIVED campaigns in API response")
                        else:
                            logger.warning(f"   ⚠️ No ARCHIVED campaigns found in API response (requested States include ARCHIVED)")
                        
                        # Check if specific campaigns are present
                        campaign_names = [c['Name'] for c in campaigns]
                        campaign_ids = [str(c['Id']) for c in campaigns]
                        logger.info(f"   🔴 Campaign names list: {campaign_names}")
                        logger.info(f"   🔴 Campaign IDs list: {campaign_ids}")
                        
                        # Check for specific campaigns user mentioned
                        if any('кси' in name.lower() or 'ksi' in name.lower() for name in campaign_names):
                            logger.info(f"   ✅ Found 'кси' campaign in results!")
                        else:
                            logger.warning(f"   ❌ 'кси' campaign NOT found in API response!")
                            logger.warning(f"   ⚠️ This might mean the campaign is in CONVERTED state or has a different issue")
                            logger.warning(f"   ⚠️ Consider using Reports API fallback to get all campaigns")
                        
                        # IMPORTANT: Keep ALL campaigns including ARCHIVED
                        # ARCHIVED campaigns should be returned so frontend filter can work
                        # Frontend will filter them using the state field
                        filtered_campaigns = campaigns  # Keep all campaigns, including ARCHIVED
                        
                        archived_count = sum(1 for c in campaigns if c.get("State") == "ARCHIVED")
                        if archived_count > 0:
                            logger.info(f"   📋 Found {archived_count} ARCHIVED campaigns (will be returned for filtering)")
                        
                        # Use Campaigns.get as primary source - it has full status/state information
                        result = [
                            {
                                "id": str(c["Id"]),
                                "name": c["Name"],
                                "status": c["Status"],
                                "state": c.get("State", "UNKNOWN"),  # Include state for filtering (ON, OFF, SUSPENDED, ENDED, ARCHIVED)
                                "status_payment": c.get("StatusPayment", "UNKNOWN"),  # Include payment status
                                "type": c.get("Type", "UNKNOWN")  # Include type for filtering (TEXT_CAMPAIGN, DYNAMIC_TEXT_CAMPAIGN, etc.)
                            }
                            for c in filtered_campaigns
                        ]
                        
                        logger.info(f"   ✅ Campaigns.get returned {len(result)} campaigns (including ARCHIVED if any)")
                        logger.info(f"   ✅ Campaign IDs from Campaigns.get: {[c['id'] for c in result]}")
                        
                        # CRITICAL: Reports API is only used to ADD missing campaigns, not replace results
                        # Reports API may miss campaigns without data for the date range
                        # So we use Campaigns.get as primary source and Reports API only as supplement
                        try:
                            reports_campaigns = await self.get_campaigns_from_reports()
                            if reports_campaigns:
                                reports_ids = {c["id"] for c in reports_campaigns}
                                campaigns_get_ids = {c["id"] for c in result}
                                
                                missing_in_campaigns_get = reports_ids - campaigns_get_ids
                                if missing_in_campaigns_get:
                                    logger.warning(f"   ⚠️ Reports API found {len(missing_in_campaigns_get)} campaigns that Campaigns.get missed: {missing_in_campaigns_get}")
                                    
                                    # ADD missing campaigns from Reports API to result (don't replace)
                                    for rc in reports_campaigns:
                                        if rc["id"] not in campaigns_get_ids:
                                            result.append({
                                                "id": rc["id"],
                                                "name": rc["name"],
                                                "status": "UNKNOWN",  # Reports API doesn't provide status
                                                "state": "UNKNOWN",  # Reports API doesn't provide state
                                                "type": "UNKNOWN"  # Reports API doesn't provide type
                                            })
                                            logger.info(f"   ✅ Added missing campaign from Reports API: ID={rc['id']}, Name='{rc['name']}'")
                                    
                                    logger.info(f"   ✅ Final result: {len(result)} campaigns total (from Campaigns.get + Reports API additions)")
                                else:
                                    logger.info(f"   ✅ All campaigns from Reports API are already in Campaigns.get results")
                        except Exception as reports_err:
                            logger.warning(f"   ⚠️ Could not check Reports API for missing campaigns: {reports_err}")
                        
                        return result
                    elif "error" in data:
                        error_code = data["error"].get("error_code")
                        error_detail = data["error"].get("error_detail", "")
                        
                        # ERROR 3228: API доступен только в режиме Директ Про
                        # Fallback to Reports API which works for all accounts
                        if error_code == 3228:
                            logger.warning(f"⚠️ Campaigns.get API not available (error 3228: {error_detail}). Falling back to Reports API...")
                            return await self.get_campaigns_from_reports()
                        
                        # If we got campaigns but missing expected ones, try Reports API as fallback
                        # This handles cases where Campaigns.get filters out campaigns that Reports API can see
                        logger.warning(f"⚠️ Campaigns.get returned error, but trying Reports API fallback to get all campaigns...")
                        try:
                            reports_campaigns = await self.get_campaigns_from_reports()
                            if reports_campaigns:
                                logger.info(f"✅ Reports API returned {len(reports_campaigns)} campaigns as fallback")
                                return reports_campaigns
                        except Exception as reports_err:
                            logger.warning(f"⚠️ Reports API fallback also failed: {reports_err}")
                        
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
        
        CRITICAL: Uses a wider date range (last 30 days) to ensure we get all campaigns,
        even if they were stopped or had no data recently. Using only yesterday's date
        fails when campaigns are stopped or have no recent activity.
        """
        logger.info("📊 Getting campaigns list via Reports API (fallback method)")
        
        # CRITICAL: Use wider date range (last 30 days) instead of just yesterday
        # This ensures we get all campaigns even if they're stopped or have no recent data
        # Using only yesterday fails when:
        # 1. Campaigns are stopped (no data for yesterday)
        # 2. Campaigns have no activity (no impressions/clicks)
        # 3. Account doesn't have Pro Direct (only Reports API works)
        from datetime import datetime, timedelta
        today = datetime.now()
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")  # Last 30 days
        date_to = today.strftime("%Y-%m-%d")
        
        logger.info(f"📊 Using date range {date_from} to {date_to} to get all campaigns (including stopped ones)")
        
        # CRITICAL: Add ClientLogin filter if client_login is set
        # This ensures we only get campaigns from the selected profile
        # CRITICAL: SelectionCriteria only contains date range
        # ClientLogin filtering is done via Client-Login header, NOT in SelectionCriteria
        # Adding ClientLogin to SelectionCriteria causes 400 Bad Request error
        selection_criteria = {
            "DateFrom": date_from,
            "DateTo": date_to
        }
        
        # Client-Login header is already set in self.headers, which is sufficient for filtering
        logger.info(f"📊 get_campaigns_from_reports: Using Client-Login header: '{self.client_login}' (header filtering only, no SelectionCriteria filter)")
        
        payload = {
            "params": {
                "SelectionCriteria": selection_criteria,
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
                
                # Find header line (contains "CampaignId" or "Campaign ID")
                header_line_idx = -1
                for idx, line in enumerate(lines):
                    if 'campaignid' in line.lower() or 'campaign id' in line.lower():
                        header_line_idx = idx
                        break
                
                # Skip header line(s) and last line (totals)
                start_idx = header_line_idx + 1 if header_line_idx >= 0 else 1
                for line in lines[start_idx:-1]:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        campaign_id = parts[0].strip()
                        campaign_name = parts[1].strip()
                        
                        # CRITICAL: Skip if it's a header value or invalid ID
                        if (campaign_id and 
                            campaign_id != '--' and 
                            campaign_id.lower() != 'campaignid' and
                            campaign_id.lower() != 'campaign id' and
                            not campaign_id.startswith('Total') and
                            campaign_id.isdigit()):  # Campaign IDs are numeric
                            campaigns_dict[campaign_id] = {
                                "id": campaign_id,
                                "name": campaign_name,
                                "status": "UNKNOWN"  # Reports API doesn't return status
                            }
                        else:
                            logger.debug(f"   ⏭️ Skipping invalid campaign entry: ID='{campaign_id}', Name='{campaign_name}'")
                
                campaigns_list = list(campaigns_dict.values())
                logger.info(f"✅ Reports API returned {len(campaigns_list)} unique campaigns")
                if campaigns_list:
                    logger.info(f"   Campaign IDs from Reports API: {[c['id'] for c in campaigns_list]}")
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

        # CRITICAL: SelectionCriteria only contains date range
        # ClientLogin filtering is done via Client-Login header, NOT in SelectionCriteria
        # According to Yandex API docs, ClientLogin filter is in Filter structure, not SelectionCriteria
        # But for Reports API, the Client-Login header is sufficient for filtering
        selection_criteria = {
            "DateFrom": date_from,
            "DateTo": date_to
        }
        
        # NOTE: ClientLogin filter should be in Filter structure, not SelectionCriteria
        # But we use Client-Login header instead, which is the standard way
        # If we need explicit filtering, we would use:
        # "Filter": [{"Field": "ClientLogin", "Operator": "EQUALS", "Values": [self.client_login]}]
        # But for now, Client-Login header is sufficient
        
        report_definition = {
            "params": {
                "SelectionCriteria": selection_criteria,
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

    async def get_campaign_goals(self, campaign_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get PriorityGoals for specific campaigns using type-specific field names.
        
        CRITICAL: PriorityGoals are accessed via type-specific field names:
        - TextCampaignFieldNames: ["PriorityGoals"] for TEXT_CAMPAIGN
        - DynamicTextCampaignFieldNames: ["PriorityGoals"] for DYNAMIC_TEXT_CAMPAIGN
        - MobileAppCampaignFieldNames: ["PriorityGoals"] for MOBILE_APP_CAMPAIGN
        - SmartCampaignFieldNames: ["PriorityGoals"] for SMART_CAMPAIGN
        
        Returns a dict mapping campaign_id to list of goals with goal_id and goal_name.
        """
        if not campaign_ids:
            return {}
        
        logger.info(f"📊 Getting PriorityGoals for {len(campaign_ids)} campaigns")
        
        # Convert campaign IDs to integers
        numeric_ids = []
        for cid in campaign_ids:
            if cid.isdigit():
                numeric_ids.append(int(cid))
            else:
                logger.warning(f"⚠️ Campaign ID '{cid}' is not numeric, skipping")
        
        if not numeric_ids:
            logger.warning(f"⚠️ No valid numeric campaign IDs found")
            return {}
        
        selection_criteria = {
            "Ids": numeric_ids
        }
        
        # CRITICAL: Request PriorityGoals for all campaign types
        # PriorityGoals are in type-specific structures, not in top-level FieldNames
        payload = {
            "method": "get",
            "params": {
                "SelectionCriteria": selection_criteria,
                "FieldNames": ["Id", "Name", "Type"],  # Get basic fields and type
                "TextCampaignFieldNames": ["PriorityGoals"],  # For TEXT_CAMPAIGN
                "DynamicTextCampaignFieldNames": ["PriorityGoals"],  # For DYNAMIC_TEXT_CAMPAIGN
                "MobileAppCampaignFieldNames": ["PriorityGoals"],  # For MOBILE_APP_CAMPAIGN
                "SmartCampaignFieldNames": ["PriorityGoals"]  # For SMART_CAMPAIGN
            }
        }
        
        campaign_goals_map = {}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.campaigns_url, json=payload, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "result" in data and "Campaigns" in data["result"]:
                        campaigns = data["result"]["Campaigns"]
                        
                        for campaign in campaigns:
                            campaign_id = str(campaign["Id"])
                            campaign_name = campaign.get("Name", "Unknown")
                            campaign_type = campaign.get("Type", "UNKNOWN")
                            
                            # Extract PriorityGoals based on campaign type
                            priority_goals = []
                            
                            if campaign_type == "TEXT_CAMPAIGN" and "TextCampaign" in campaign:
                                priority_goals = campaign["TextCampaign"].get("PriorityGoals", [])
                            elif campaign_type == "DYNAMIC_TEXT_CAMPAIGN" and "DynamicTextCampaign" in campaign:
                                priority_goals = campaign["DynamicTextCampaign"].get("PriorityGoals", [])
                            elif campaign_type == "MOBILE_APP_CAMPAIGN" and "MobileAppCampaign" in campaign:
                                priority_goals = campaign["MobileAppCampaign"].get("PriorityGoals", [])
                            elif campaign_type == "SMART_CAMPAIGN" and "SmartCampaign" in campaign:
                                priority_goals = campaign["SmartCampaign"].get("PriorityGoals", [])
                            
                            # Format goals to include goal_id and goal_name
                            goals_list = []
                            for goal in priority_goals:
                                # PriorityGoals structure: {"GoalId": "123", "Name": "Goal Name", "Value": 100}
                                goal_id = str(goal.get("GoalId", ""))
                                goal_name = goal.get("Name", f"Goal {goal_id}")
                                if goal_id:
                                    goals_list.append({
                                        "goal_id": goal_id,
                                        "goal_name": goal_name
                                    })
                            
                            campaign_goals_map[campaign_id] = goals_list
                            if goals_list:
                                logger.info(f"   ✅ Campaign {campaign_id} ({campaign_name}): {len(goals_list)} priority goals")
                            else:
                                logger.info(f"   ⚠️ Campaign {campaign_id} ({campaign_name}): no PriorityGoals found")
                        
                        logger.info(f"📊 Successfully fetched PriorityGoals for {len(campaign_goals_map)} campaigns")
                        return campaign_goals_map
                    
                    elif "error" in data:
                        error_code = data["error"].get("error_code")
                        error_detail = data["error"].get("error_detail", "")
                        
                        if error_code == 3228:
                            logger.warning(f"⚠️ Campaigns.get not available (error 3228: {error_detail}). Account likely does not have Direct Pro.")
                            return {}  # Return empty to trigger fallback
                        
                        error_msg = json.dumps(data["error"])
                        logger.error(f"Yandex API Error fetching campaign goals: {error_msg}")
                        raise Exception(f"Yandex API Error: {error_msg}")
                    else:
                        logger.warning(f"No campaigns found for IDs: {campaign_ids}")
                        return {}
                
                else:
                    error_msg = f"Failed to fetch Yandex campaign goals: {response.status_code} - {response.text[:200]}"
                    logger.error(error_msg)
                    if response.status_code == 401:
                        raise PermissionError(f"Unauthorized: {error_msg}")
                    elif response.status_code == 403:
                        raise PermissionError(f"Forbidden: {error_msg}")
                    raise Exception(error_msg)
                    
            except PermissionError:
                raise
            except Exception as e:
                # Check if it's a Direct Pro error
                if "error_code\":3228" in str(e) or "Директ Про" in str(e) or "3228" in str(e):
                    logger.warning(f"⚠️ Cannot get PriorityGoals (Direct Pro not available). Will use fallback method.")
                    return {}
                logger.error(f"Error fetching campaign goals: {e}")
                # Don't raise - return empty to trigger fallback
                logger.warning(f"⚠️ Error getting campaign goals, will use fallback method: {e}")
                return {}
    
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
