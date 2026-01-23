import httpx
import json
import asyncio
from datetime import date, datetime
from typing import List, Dict, Any, Optional
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
        self.ads_url = "https://api.direct.yandex.com/json/v5/ads"
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
        
        logger.info("=" * 80)
        logger.info("🚀 YandexDirectAPI.get_campaigns: STARTING")
        logger.info(f"🚀 Client-Login: '{self.client_login}'")
        
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
                response = await client.post(self.campaigns_url, json=payload, headers=self.headers, timeout=120.0)
                
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
                        result = []
                        for c in filtered_campaigns:
                            campaign_state = c.get("State")
                            campaign_status = c.get("Status")
                            campaign_type = c.get("Type")
                            
                            # CRITICAL: Log if State is missing
                            if campaign_state is None:
                                logger.warning(f"   ⚠️ Campaign {c['Id']} ('{c['Name']}') has NO State field in API response!")
                                logger.warning(f"   ⚠️ Available fields: {list(c.keys())}")
                            
                            result.append({
                                "id": str(c["Id"]),
                                "name": c["Name"],
                                "status": campaign_status if campaign_status is not None else "UNKNOWN",
                                "state": campaign_state if campaign_state is not None else "UNKNOWN",  # Include state for filtering (ON, OFF, SUSPENDED, ENDED, ARCHIVED)
                                "status_payment": c.get("StatusPayment", "UNKNOWN"),  # Include payment status
                                "type": campaign_type if campaign_type is not None else "UNKNOWN"  # Include type for filtering (TEXT_CAMPAIGN, DYNAMIC_TEXT_CAMPAIGN, etc.)
                            })
                        
                        logger.info(f"   ✅ Campaigns.get returned {len(result)} campaigns (including ARCHIVED if any)")
                        logger.info(f"   ✅ Campaign IDs from Campaigns.get: {[c['id'] for c in result]}")
                        logger.info(f"   ✅ Campaign names from Campaigns.get: {[c['name'] for c in result]}")
                        
                        # CRITICAL: Always check Reports API to find campaigns that Campaigns.get might miss
                        # This is especially important for accounts using Redirect API (OAuth flow)
                        # Reports API may find campaigns that Campaigns.get doesn't return due to:
                        # - Different filtering logic
                        # - Campaigns without recent activity
                        # - Campaigns in specific states that Campaigns.get filters out
                        logger.info(f"   📊 Checking Reports API for additional campaigns...")
                        try:
                            reports_campaigns = await self.get_campaigns_from_reports()
                            if reports_campaigns:
                                logger.info(f"   📊 Reports API returned {len(reports_campaigns)} campaigns")
                                logger.info(f"   📊 Reports API campaign IDs: {[c['id'] for c in reports_campaigns]}")
                                logger.info(f"   📊 Reports API campaign names: {[c['name'] for c in reports_campaigns]}")
                                
                                reports_ids = {c["id"] for c in reports_campaigns}
                                campaigns_get_ids = {c["id"] for c in result}
                                
                                missing_in_campaigns_get = reports_ids - campaigns_get_ids
                                if missing_in_campaigns_get:
                                    logger.warning(f"   ⚠️ Reports API found {len(missing_in_campaigns_get)} campaigns that Campaigns.get missed!")
                                    logger.warning(f"   ⚠️ Missing campaign IDs: {missing_in_campaigns_get}")
                                    
                                    # CRITICAL: Fetch status/state for missing campaigns via Campaigns.get by ID
                                    # Reports API doesn't provide status/state, so we need to query Campaigns.get
                                    missing_ids_list = list(missing_in_campaigns_get)
                                    logger.info(f"   📊 Fetching status/state for {len(missing_ids_list)} missing campaigns via Campaigns.get...")
                                    
                                    try:
                                        # Query Campaigns.get for specific campaign IDs
                                        # CRITICAL: Some campaigns (especially Smart Campaigns) might not be returned
                                        # even when queried by ID if they are in certain states (CONVERTED, DELETED, etc.)
                                        missing_ids_int = [int(cid) for cid in missing_ids_list if cid.isdigit()]
                                        if not missing_ids_int:
                                            status_map = {}
                                            logger.warning(f"   ⚠️ No valid numeric IDs to query")
                                        else:
                                            # Try with minimal FieldNames first (faster)
                                            status_payload = {
                                                "method": "get",
                                                "params": {
                                                    "SelectionCriteria": {
                                                        "Ids": missing_ids_int
                                                        # CRITICAL: Don't filter by States - we want ALL campaigns
                                                    },
                                                    "FieldNames": ["Id", "Name", "Status", "State", "StatusPayment", "Type"]
                                                }
                                            }
                                            
                                            logger.info(f"   📊 Querying Campaigns.get for {len(missing_ids_int)} campaigns by ID...")
                                            status_response = await client.post(self.campaigns_url, json=status_payload, headers=self.headers, timeout=120.0)
                                            
                                            if status_response.status_code == 200:
                                                status_data = status_response.json()
                                                if "result" in status_data and "Campaigns" in status_data["result"]:
                                                    status_campaigns = status_data["result"]["Campaigns"]
                                                    status_map = {str(c["Id"]): c for c in status_campaigns}
                                                    logger.info(f"   ✅ Successfully fetched status for {len(status_campaigns)} campaigns")
                                                    logger.info(f"   📊 Status query returned campaign IDs: {[str(c['Id']) for c in status_campaigns]}")
                                                    
                                                    # Log which campaigns were NOT found
                                                    requested_ids_set = set(missing_ids_int)
                                                    found_ids_set = {c["Id"] for c in status_campaigns}
                                                    missing_in_status = requested_ids_set - found_ids_set
                                                    if missing_in_status:
                                                        logger.warning(f"   ⚠️ Status query did NOT return {len(missing_in_status)} campaigns: {missing_in_status}")
                                                        logger.warning(f"   ⚠️ These campaigns are likely in CONVERTED, DELETED, or another state that Campaigns.get filters out")
                                                        logger.warning(f"   ⚠️ They exist in Reports API (have data), so they will be displayed with UNKNOWN status")
                                                else:
                                                    status_map = {}
                                                    logger.warning(f"   ⚠️ No campaigns returned from status query")
                                                    if "error" in status_data:
                                                        logger.error(f"   ❌ Status query error: {status_data['error']}")
                                                    else:
                                                        logger.warning(f"   ⚠️ API returned 200 but no campaigns in result. Full response: {status_data}")
                                            else:
                                                status_map = {}
                                                logger.warning(f"   ⚠️ Failed to fetch status: {status_response.status_code}")
                                                try:
                                                    error_text = status_response.text
                                                    logger.error(f"   ❌ Status query error response: {error_text}")
                                                except:
                                                    pass
                                    except Exception as status_err:
                                        status_map = {}
                                        logger.warning(f"   ⚠️ Error fetching status for missing campaigns: {status_err}")
                                        import traceback
                                        logger.error(f"   ❌ Traceback: {traceback.format_exc()}")
                                    
                                    # ADD missing campaigns from Reports API to result (don't replace)
                                    for rc in reports_campaigns:
                                        if rc["id"] not in campaigns_get_ids:
                                            # Try to get state/type from status query if available
                                            status_campaign = status_map.get(rc["id"])
                                            if status_campaign:
                                                result.append({
                                                    "id": rc["id"],
                                                    "name": rc["name"],
                                                    "status": status_campaign.get("Status", "UNKNOWN"),
                                                    "state": status_campaign.get("State", "UNKNOWN"),
                                                    "status_payment": status_campaign.get("StatusPayment", "UNKNOWN"),
                                                    "type": status_campaign.get("Type", "UNKNOWN")
                                                })
                                                logger.info(f"   ✅ Added missing campaign with status: ID={rc['id']}, Name='{rc['name']}', State={status_campaign.get('State', 'UNKNOWN')}")
                                            else:
                                                # Fallback to UNKNOWN if status query failed
                                                result.append({
                                                    "id": rc["id"],
                                                    "name": rc["name"],
                                                    "status": "UNKNOWN",
                                                    "state": "UNKNOWN",
                                                    "type": "UNKNOWN"
                                                })
                                                logger.info(f"   ✅ Added missing campaign (no status): ID={rc['id']}, Name='{rc['name']}'")
                                    
                                    logger.info(f"   ✅ Final result: {len(result)} campaigns total (from Campaigns.get + Reports API additions)")
                                else:
                                    logger.info(f"   ✅ All campaigns from Reports API are already in Campaigns.get results")
                            else:
                                logger.warning(f"   ⚠️ Reports API returned 0 campaigns (this might indicate a filtering issue)")
                        except Exception as reports_err:
                            logger.error(f"   ❌ Could not check Reports API for missing campaigns: {reports_err}")
                            logger.error(f"   ❌ Reports API error details: {type(reports_err).__name__}: {str(reports_err)}")
                        
                        logger.info(f"   ✅ Returning {len(result)} total campaigns (from Campaigns.get + Reports API)")
                        logger.info(f"   ✅ Final campaign names: {[c['name'] for c in result]}")
                        logger.info(f"   ✅ Final campaign IDs: {[c['id'] for c in result]}")
                        logger.info("=" * 60)
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

    async def get_campaigns_from_reports(self, retry_count: int = 0) -> List[Dict[str, Any]]:
        """
        FALLBACK METHOD: Get campaigns list using Reports API.
        This works for ALL Yandex Direct accounts, including those in new interface.
        
        CRITICAL: Uses a wide date range (last 5 years) to ensure we get ALL campaigns,
        even if they were stopped long ago or had no data recently. This ensures we find
        all campaigns that were ever active, regardless of when they were last active.
        
        Args:
            retry_count: Internal counter to prevent infinite recursion on error 4000
        """
        if retry_count > 2:
            logger.error("❌ Too many retries for Reports API (error 4000). Returning empty list.")
            return []
        
        logger.info("📊 Getting campaigns list via Reports API (fallback method)")
        
        # CRITICAL: Reports API limitation - it only returns campaigns WITH DATA for the specified period
        # If campaigns have NO data (never had impressions/clicks), they won't appear in reports
        # This is a known limitation of Yandex Direct Reports API
        # 
        # We try multiple approaches:
        # 1. Very wide date range (10 years) to catch campaigns with old data
        # 2. If that doesn't work, we note that some campaigns may be missing due to API limitations
        
        from datetime import datetime, timedelta
        today = datetime.now()
        
        # Try 10 years to catch campaigns with very old data
        date_from = (today - timedelta(days=3650)).strftime("%Y-%m-%d")  # Last 10 years
        date_to = today.strftime("%Y-%m-%d")
        
        logger.info(f"📊 Using date range {date_from} to {date_to} (last 10 years) to get ALL campaigns (including stopped ones)")
        logger.warning(f"⚠️ IMPORTANT: Reports API only returns campaigns WITH DATA. Campaigns without any data won't appear!")
        
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
        
        # DEBUG: Log headers that will be sent (mask Authorization)
        debug_headers = dict(self.headers)
        if 'Authorization' in debug_headers:
            debug_headers['Authorization'] = 'Bearer [REDACTED]'
        logger.info(f"📊 Reports API request headers: {debug_headers}")
        logger.info(f"📊 Reports API Client-Login header value: '{self.headers.get('Client-Login', 'NOT SET')}'")
        
        # CRITICAL: Use unique report name to avoid "report already in queue" error (4000)
        # Each request needs a unique name, otherwise API returns error if previous report is still processing
        import time
        unique_report_name = f"Campaign List Report {int(time.time() * 1000)}"
        
        payload = {
            "params": {
                "SelectionCriteria": selection_criteria,
                "FieldNames": ["CampaignId", "CampaignName"],
                "ReportName": unique_report_name,
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "DateRangeType": "CUSTOM_DATE",
                "Format": "TSV",
                "IncludeVAT": "NO",
                "IncludeDiscount": "NO"
            }
        }
        
        logger.info(f"📊 Reports API payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.report_url,
                json=payload,
                headers=self.headers,
                timeout=60.0
            )
            
            logger.info(f"📊 Reports API response status: {response.status_code}")
            
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
                    timeout=120.0
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
                                "status": "UNKNOWN",  # Reports API doesn't return status - will be fetched via Campaigns.get
                                "state": "UNKNOWN",  # Reports API doesn't return state - will be fetched via Campaigns.get
                                "type": "UNKNOWN"  # Reports API doesn't return type - will be fetched via Campaigns.get
                            }
                        else:
                            logger.debug(f"   ⏭️ Skipping invalid campaign entry: ID='{campaign_id}', Name='{campaign_name}'")
                
                campaigns_list = list(campaigns_dict.values())
                logger.info(f"✅ Reports API returned {len(campaigns_list)} unique campaigns")
                if campaigns_list:
                    logger.info(f"   📊 Campaign IDs from Reports API: {[c['id'] for c in campaigns_list]}")
                    logger.info(f"   📊 Campaign names from Reports API: {[c['name'] for c in campaigns_list]}")
                    logger.warning(f"   ⚠️ IMPORTANT: Reports API only returns campaigns WITH DATA!")
                    logger.warning(f"   ⚠️ Campaigns without any data (never had impressions/clicks) won't appear in this list!")
                    logger.warning(f"   ⚠️ This is a known limitation of Yandex Direct Reports API")
                    
                    # CRITICAL: Fetch status/state for campaigns from Reports API
                    # Reports API doesn't provide status/state, so we need to query Campaigns.get
                    campaign_ids_list = [int(c["id"]) for c in campaigns_list if c["id"].isdigit()]
                    if campaign_ids_list:
                        logger.info(f"   📊 Fetching status/state for {len(campaign_ids_list)} campaigns via Campaigns.get...")
                        try:
                            status_payload = {
                                "method": "get",
                                "params": {
                                    "SelectionCriteria": {
                                        "Ids": campaign_ids_list
                                    },
                                    "FieldNames": ["Id", "Name", "Status", "State", "StatusPayment", "Type"]
                                }
                            }
                            
                            status_response = await client.post(self.campaigns_url, json=status_payload, headers=self.headers, timeout=120.0)
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                
                                # Check for Direct Pro error (3228)
                                if "error" in status_data:
                                    error_info = status_data["error"]
                                    error_code = error_info.get("error_code")
                                    error_detail = error_info.get("error_detail", "")
                                    
                                    if error_code == 3228:
                                        logger.warning(f"   ⚠️ Direct Pro not available (error 3228: {error_detail})")
                                        logger.warning(f"   ⚠️ Cannot fetch status/state for campaigns from Reports API without Direct Pro")
                                        logger.warning(f"   ⚠️ Campaigns will be displayed with UNKNOWN status (they exist and have data)")
                                        # Leave campaigns with UNKNOWN status - they exist in Reports API
                                    else:
                                        logger.error(f"   ❌ Status query error: {error_info}")
                                elif "result" in status_data and "Campaigns" in status_data["result"]:
                                    status_campaigns = status_data["result"]["Campaigns"]
                                    status_map = {str(c["Id"]): c for c in status_campaigns}
                                    logger.info(f"   ✅ Successfully fetched status for {len(status_campaigns)} campaigns")
                                    logger.info(f"   📊 Status query returned campaigns: {[str(c['Id']) for c in status_campaigns]}")
                                    
                                    # Log which campaigns were NOT found in status query
                                    requested_ids = {str(c["id"]) for c in campaigns_list}
                                    found_ids = {str(c["Id"]) for c in status_campaigns}
                                    missing_ids = requested_ids - found_ids
                                    if missing_ids:
                                        logger.warning(f"   ⚠️ Status query did NOT return {len(missing_ids)} campaigns: {missing_ids}")
                                        logger.warning(f"   ⚠️ This might mean these campaigns are in a state that Campaigns.get filters out")
                                    
                                    # Update campaigns_list with status/state from Campaigns.get
                                    for campaign in campaigns_list:
                                        status_campaign = status_map.get(campaign["id"])
                                        if status_campaign:
                                            campaign["status"] = status_campaign.get("Status", "UNKNOWN")
                                            campaign_state = status_campaign.get("State")
                                            if campaign_state is None:
                                                logger.warning(f"   ⚠️ Campaign {campaign['id']} ('{campaign['name']}') has NO State in status query response!")
                                            campaign["state"] = campaign_state if campaign_state is not None else "UNKNOWN"
                                            campaign["status_payment"] = status_campaign.get("StatusPayment", "UNKNOWN")
                                            campaign["type"] = status_campaign.get("Type", "UNKNOWN")
                                            logger.info(f"   ✅ Updated campaign {campaign['id']}: State={campaign['state']}, Status={campaign['status']}")
                                        else:
                                            # Keep UNKNOWN if not found
                                            logger.warning(f"   ⚠️ Campaign {campaign['id']} ('{campaign['name']}') NOT found in status query response!")
                                            campaign["status"] = "UNKNOWN"
                                            campaign["state"] = "UNKNOWN"
                                            campaign["type"] = "UNKNOWN"
                                else:
                                    logger.warning(f"   ⚠️ No campaigns returned from status query")
                            else:
                                logger.warning(f"   ⚠️ Failed to fetch status: {status_response.status_code}")
                                try:
                                    error_text = status_response.text
                                    logger.error(f"   ❌ Status query error response: {error_text}")
                                    # Check if it's a Direct Pro error in response text
                                    if "3228" in error_text or "Директ Про" in error_text:
                                        logger.warning(f"   ⚠️ Direct Pro not available. Campaigns will have UNKNOWN status.")
                                except:
                                    pass
                        except Exception as status_err:
                            logger.warning(f"   ⚠️ Error fetching status for Reports API campaigns: {status_err}")
                else:
                    logger.warning(f"   ⚠️ Reports API returned 0 campaigns - this might indicate:")
                    logger.warning(f"      - Client-Login header filtering is too strict")
                    logger.warning(f"      - No campaigns have data in the date range ({date_from} to {date_to})")
                    logger.warning(f"      - Account doesn't have access to campaigns via Reports API")
                return campaigns_list
            
            elif response.status_code == 400:
                error_data = response.text
                logger.error(f"Reports API error 400: {error_data}")
                
                # Check if it's error 4000 (report name conflict)
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_code = error_json["error"].get("error_code")
                        if error_code == 4000:
                            # Report with same name is already in queue - retry with new unique name
                            logger.warning(f"⚠️ Report name conflict (4000). Retrying with new unique name... (attempt {retry_count + 1}/3)")
                            # Recursively retry with new unique name (will generate new timestamp)
                            return await self.get_campaigns_from_reports(retry_count=retry_count + 1)
                except:
                    pass
                
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

        # Увеличиваем таймаут для больших периодов (90+ дней)
        # Для 90 дней: 300 секунд (5 минут), для больших периодов - еще больше
        date_range_days = (dt_to - dt_from).days
        if date_range_days > 90:
            timeout_seconds = min(600.0, 120.0 + (date_range_days - 90) * 2)  # Максимум 10 минут
            logger.info(f"Using extended timeout {timeout_seconds}s for {date_range_days}-day period")
        else:
            timeout_seconds = 120.0
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                response = await client.post(
                    self.report_url,
                    json=report_definition,
                    headers=self.headers,
                    timeout=timeout_seconds
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

    async def get_campaign_counters(self, campaign_ids: List[str]) -> Dict[str, List[str]]:
        """
        Get attached Metrica counters (CounterIds) for specific campaigns.
        
        This does NOT require Direct Pro and работает для обычных аккаунтов:
        - поле CounterIds находится внутри типо-специфичных объектов кампаний
          (TextCampaign, DynamicTextCampaign, SmartCampaign и т.д.).
        
        Returns dict: campaign_id (str) -> list of counter_id (str).
        """
        if not campaign_ids:
            return {}
        
        # Минимальное логирование для производительности
        
        numeric_ids: List[int] = []
        for cid in campaign_ids:
            if isinstance(cid, str) and cid.isdigit():
                numeric_ids.append(int(cid))
            else:
                logger.warning(f"⚠️ get_campaign_counters: campaign ID '{cid}' is not numeric, skipping")
        
        if not numeric_ids:
            logger.warning("⚠️ get_campaign_counters: no valid numeric campaign IDs after filtering")
            return {}
        
        selection_criteria = {
            "Ids": numeric_ids
        }
        
        # Поля для счётчиков Метрики:
        # - для текстовых и динамических кампаний используется CounterIds (массив)
        # - для смарт‑кампаний используется CounterId (одно значение)
        payload = {
            "method": "get",
            "params": {
                "SelectionCriteria": selection_criteria,
                "FieldNames": ["Id", "Name", "Type"],
                "TextCampaignFieldNames": ["CounterIds"],
                "DynamicTextCampaignFieldNames": ["CounterIds"],
                # Для мобильных кампаний поле может отсутствовать — не критично.
                "SmartCampaignFieldNames": ["CounterId"]
            }
        }
        
        result: Dict[str, List[str]] = {}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.campaigns_url, json=payload, headers=self.headers, timeout=120.0)
                
                if response.status_code != 200:
                    logger.error(f"get_campaign_counters failed: {response.status_code}")
                    return {}
                
                data = response.json()
                if "error" in data:
                    error_code = data["error"].get("error_code")
                    if error_code == 3228:
                        # Direct Pro not available - expected, will use fallback
                        return {}
                    logger.error(f"get_campaign_counters API error: {data['error'].get('error_detail', 'Unknown')}")
                    return {}
                
                campaigns = data.get("result", {}).get("Campaigns", [])
                logger.info(f"get_campaign_counters: got {len(campaigns)} campaigns from API")
                
                for campaign in campaigns:
                    cid = str(campaign.get("Id"))
                    name = campaign.get("Name", "Unknown")
                    ctype = campaign.get("Type", "UNKNOWN")
                    
                    counter_ids: List[str] = []
                    
                    # CounterIds / CounterId может быть списком, одним значением или вложенным объектом вида {"Items": [..]}
                    def _extract_ids(container: Dict[str, Any]) -> List[str]:
                        # Проверяем оба варианта: CounterIds (множественное) и CounterId (единственное)
                        raw = container.get("CounterIds") or container.get("CounterId")
                        if not raw:
                            return []
                        
                        # Вариант 1: уже список ID
                        if isinstance(raw, list):
                            return [str(x) for x in raw if x]
                        
                        # Вариант 2: объект с ключом Items: {"Items": [77748790, ...]}
                        if isinstance(raw, dict) and "Items" in raw:
                            items = raw.get("Items") or []
                            if isinstance(items, list):
                                return [str(x) for x in items if x]
                        
                        # Вариант 3: строка формата "{'Items': [77748790, 90692688]}"
                        if isinstance(raw, str):
                            import re, ast
                            # Пытаемся безопасно распарсить как питоновский литерал
                            try:
                                parsed = ast.literal_eval(raw)
                                if isinstance(parsed, dict) and "Items" in parsed:
                                    items = parsed.get("Items") or []
                                    if isinstance(items, list):
                                        return [str(x) for x in items if x]
                            except Exception:
                                # Фоллбек: просто вытащим все числа из строки
                                ids = re.findall(r"\d+", raw)
                                return ids
                        
                        # Последний фоллбек — трактуем как одиночный ID
                        return [str(raw)]
                    
                    # Извлекаем CounterIds в зависимости от типа кампании
                    campaign_container = None
                    if ctype == "TEXT_CAMPAIGN" and "TextCampaign" in campaign:
                        campaign_container = campaign["TextCampaign"]
                    elif ctype == "DYNAMIC_TEXT_CAMPAIGN" and "DynamicTextCampaign" in campaign:
                        campaign_container = campaign["DynamicTextCampaign"]
                    elif ctype == "SMART_CAMPAIGN" and "SmartCampaign" in campaign:
                        campaign_container = campaign["SmartCampaign"]
                    else:
                        # Для других типов пробуем найти любой доступный контейнер
                        campaign_container = campaign.get("TextCampaign") or campaign.get("DynamicTextCampaign") or campaign.get("SmartCampaign")
                    
                    if campaign_container:
                        counter_ids = _extract_ids(campaign_container)
                        # Логируем структуру контейнера для отладки
                        if not counter_ids:
                            logger.debug(f"Campaign {cid} ({name}, type={ctype}): no CounterIds found. Container keys: {list(campaign_container.keys())}")
                    else:
                        logger.debug(f"Campaign {cid} ({name}, type={ctype}): no campaign container found. Campaign keys: {list(campaign.keys())}")
                    
                    if counter_ids:
                        result[cid] = counter_ids
                        logger.info(f"Campaign {cid} ({name}): found CounterIds={counter_ids}")
                
                logger.info(f"get_campaign_counters: returning {len(result)} campaigns with counters")
                return result
            except Exception as e:
                logger.error(f"get_campaign_counters exception: {e}")
                return {}
    
    async def get_campaign_domains(self, campaign_ids: List[str]) -> set:
        """
        Get unique domains from selected campaigns by fetching their ads and extracting Href URLs.
        
        Returns set of normalized domains (e.g., {'kxi-stroi.rf', 'example.com'}).
        """
        if not campaign_ids:
            return set()
        
        logger.info(f"Getting domains for {len(campaign_ids)} campaigns")
        
        numeric_ids = []
        for cid in campaign_ids:
            if isinstance(cid, str) and cid.isdigit():
                numeric_ids.append(int(cid))
        
        if not numeric_ids:
            return set()
        
        # Helper to normalize domain from URL
        def normalize_domain(url: str) -> str:
            """Extract and normalize domain from URL"""
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
        
        domains = set()
        
        async with httpx.AsyncClient() as client:
            try:
                # Request ads for these campaigns
                payload = {
                    "method": "get",
                    "params": {
                        "SelectionCriteria": {
                            "CampaignIds": numeric_ids
                        },
                        "FieldNames": ["Id", "CampaignId"],
                        "TextAdFieldNames": ["Href", "DisplayUrlPath"],
                        "DynamicTextAdFieldNames": ["Href", "DisplayUrlPath"],
                        "MobileAppAdFieldNames": ["TrackingUrl"],
                        "SmartAdFieldNames": ["Href"]
                    }
                }
                
                response = await client.post(self.ads_url, json=payload, headers=self.headers, timeout=120.0)
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data and "Ads" in data["result"]:
                        ads = data["result"]["Ads"]
                        logger.info(f"Got {len(ads)} ads for domain extraction")
                        
                        for ad in ads:
                            # Try different ad types
                            href = None
                            if "TextAd" in ad:
                                href = ad["TextAd"].get("Href") or ad["TextAd"].get("DisplayUrlPath")
                            elif "DynamicTextAd" in ad:
                                href = ad["DynamicTextAd"].get("Href") or ad["DynamicTextAd"].get("DisplayUrlPath")
                            elif "MobileAppAd" in ad:
                                href = ad["MobileAppAd"].get("TrackingUrl")
                            elif "SmartAd" in ad:
                                href = ad["SmartAd"].get("Href")
                            
                            if href:
                                domain = normalize_domain(href)
                                if domain:
                                    domains.add(domain)
                                    logger.debug(f"Extracted domain '{domain}' from ad {ad.get('Id')}")
                        
                        if domains:
                            logger.info(f"Extracted {len(domains)} unique domains from Ads.get: {list(domains)}")
                            return domains
                        else:
                            logger.warning("Ads.get returned ads but no Href URLs found")
                    else:
                        logger.warning("No ads found in Ads.get API response")
                
                # Fallback: Try to get campaign names and extract domains from them (if they contain URLs)
                # This is a heuristic approach - sometimes campaign names contain domain hints
                logger.info("Trying to extract domains from campaign names as fallback")
                try:
                    campaign_payload = {
                        "method": "get",
                        "params": {
                            "SelectionCriteria": {
                                "Ids": numeric_ids
                            },
                            "FieldNames": ["Id", "Name"]
                        }
                    }
                    
                    campaign_response = await client.post(self.campaigns_url, json=campaign_payload, headers=self.headers, timeout=120.0)
                    if campaign_response.status_code == 200:
                        campaign_data = campaign_response.json()
                        if "result" in campaign_data and "Campaigns" in campaign_data["result"]:
                            import re
                            url_pattern = re.compile(r'https?://([^\s/]+)')
                            for campaign in campaign_data["result"]["Campaigns"]:
                                campaign_name = campaign.get("Name", "")
                                # Try to find URLs in campaign name
                                matches = url_pattern.findall(campaign_name)
                                for match in matches:
                                    domain = normalize_domain(match)
                                    if domain:
                                        domains.add(domain)
                                        logger.debug(f"Extracted domain '{domain}' from campaign name '{campaign_name}'")
                except Exception as name_err:
                    logger.debug(f"Could not extract domains from campaign names: {name_err}")
                
                # Fallback: Try Reports API to get Href from keyword/group reports
                if not domains:
                    logger.info("Trying Reports API fallback to get campaign domains")
                    try:
                        from datetime import datetime, timedelta
                        # Use recent date range (last 30 days) to get active ads
                        date_to = datetime.now().date()
                        date_from = date_to - timedelta(days=30)
                        
                        report_definition = {
                            "params": {
                                "SelectionCriteria": {
                                    "DateFrom": date_from.strftime("%Y-%m-%d"),
                                    "DateTo": date_to.strftime("%Y-%m-%d"),
                                    "CampaignIds": numeric_ids
                                },
                                "FieldNames": ["Date", "CampaignId", "CampaignName"],
                                "ReportName": f"DomainExtraction_{int(datetime.now().timestamp())}",
                                "ReportType": "KEYWORDS_PERFORMANCE_REPORT",
                                "DateRangeType": "CUSTOM_DATE",
                                "Format": "TSV",
                                "IncludeVAT": "NO"
                            }
                        }
                        
                        report_response = await client.post(
                            self.report_url,
                            json=report_definition,
                            headers=self.headers,
                            timeout=120.0
                        )
                        
                        if report_response.status_code in [200, 201, 202]:
                            # Handle async report generation
                            if report_response.status_code in [201, 202]:
                                retry_after = int(report_response.headers.get("Retry-After", 5))
                                logger.info(f"Report is generating, waiting {retry_after}s...")
                                await asyncio.sleep(retry_after)
                                # Retry once
                                report_response = await client.post(
                                    self.report_url,
                                    json=report_definition,
                                    headers=self.headers,
                                    timeout=120.0
                                )
                            
                            if report_response.status_code == 200:
                                tsv_data = report_response.text
                                lines = tsv_data.strip().split('\n')
                                
                                # Find header row to locate Href column
                                header_found = False
                                href_col_index = -1
                                
                                for line_idx, line in enumerate(lines):
                                    if not line.strip():
                                        continue
                                    
                                    cols = line.split('\t')
                                    
                                    # Look for header row
                                    if not header_found and "Href" in line:
                                        header_found = True
                                        try:
                                            href_col_index = cols.index("Href")
                                            logger.debug(f"Found Href column at index {href_col_index}")
                                        except ValueError:
                                            # Try case-insensitive search
                                            for i, col in enumerate(cols):
                                                if "href" in col.lower():
                                                    href_col_index = i
                                                    logger.debug(f"Found Href column (case-insensitive) at index {href_col_index}")
                                                    break
                                        continue
                                    
                                    # Skip header and summary rows
                                    if line.startswith("Date") or "Total" in line or len(cols) < 3:
                                        continue
                                    
                                    # Extract domain from Href column if we found it
                                    if href_col_index >= 0 and href_col_index < len(cols):
                                        href = cols[href_col_index].strip()
                                        if href and ('http://' in href or 'https://' in href):
                                            domain = normalize_domain(href)
                                            if domain:
                                                domains.add(domain)
                                                logger.debug(f"Extracted domain '{domain}' from Reports API Href column")
                                    
                                    # Also try to find URLs in any column (fallback)
                                    for col in cols:
                                        if col and ('http://' in col or 'https://' in col):
                                            domain = normalize_domain(col)
                                            if domain:
                                                domains.add(domain)
                                                logger.debug(f"Extracted domain '{domain}' from Reports API (any column)")
                                
                                if domains:
                                    logger.info(f"Extracted {len(domains)} unique domains from Reports API: {list(domains)}")
                                    return domains
                                else:
                                    logger.warning("Reports API returned data but no Href URLs found")
                            else:
                                logger.warning(f"Reports API returned status {report_response.status_code}")
                        else:
                            # Log error details
                            try:
                                error_data = report_response.json()
                                error_detail = error_data.get("error", {}).get("error_detail", error_data.get("error", "Unknown error"))
                                logger.warning(f"Reports API fallback failed: {report_response.status_code} - {error_detail}")
                            except:
                                logger.warning(f"Reports API fallback failed: {report_response.status_code} - {report_response.text[:200]}")
                            
                            # Try alternative: AD_PERFORMANCE_REPORT instead of KEYWORDS_PERFORMANCE_REPORT
                            logger.info("Trying AD_PERFORMANCE_REPORT as alternative")
                            try:
                                alt_report_definition = {
                                    "params": {
                                        "SelectionCriteria": {
                                            "DateFrom": date_from.strftime("%Y-%m-%d"),
                                            "DateTo": date_to.strftime("%Y-%m-%d"),
                                            "CampaignIds": numeric_ids
                                        },
                                        "FieldNames": ["Date", "CampaignId", "CampaignName", "AdId", "AdType"],
                                        "ReportName": f"DomainExtraction_Ad_{int(datetime.now().timestamp())}",
                                        "ReportType": "AD_PERFORMANCE_REPORT",
                                        "DateRangeType": "CUSTOM_DATE",
                                        "Format": "TSV",
                                        "IncludeVAT": "NO"
                                    }
                                }
                                
                                alt_response = await client.post(
                                    self.report_url,
                                    json=alt_report_definition,
                                    headers=self.headers,
                                    timeout=120.0
                                )
                                
                                if alt_response.status_code in [200, 201, 202]:
                                    if alt_response.status_code in [201, 202]:
                                        retry_after = int(alt_response.headers.get("Retry-After", 5))
                                        logger.info(f"AD_PERFORMANCE_REPORT is generating, waiting {retry_after}s...")
                                        await asyncio.sleep(retry_after)
                                        alt_response = await client.post(
                                            self.report_url,
                                            json=alt_report_definition,
                                            headers=self.headers,
                                            timeout=120.0
                                        )
                                    
                                    if alt_response.status_code == 200:
                                        # AD_PERFORMANCE_REPORT doesn't have Href, but we can try to get ad IDs
                                        # and then fetch ads via Ads.get to get Href
                                        logger.info("AD_PERFORMANCE_REPORT returned data, but Href not available in this report type")
                                        # Note: We could fetch ad IDs and then use Ads.get, but that's redundant
                                        # since we already tried Ads.get above. Skip this path.
                            except Exception as alt_err:
                                logger.debug(f"AD_PERFORMANCE_REPORT alternative also failed: {alt_err}")
                    except Exception as report_err:
                        logger.warning(f"Reports API fallback error: {report_err}")
                
                # If both methods failed, return empty set
                logger.warning(f"Could not extract domains from {len(campaign_ids)} campaigns (Ads.get and Reports API both failed)")
                return set()
            except Exception as e:
                logger.error(f"Error getting campaign domains: {e}")
                return set()

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
        
        # CRITICAL: Request PriorityGoals only for campaign types that support it
        # MOBILE_APP_CAMPAIGN does NOT support PriorityGoals (causes error 8000)
        # First, get campaign types, then request PriorityGoals only for supported types
        payload = {
            "method": "get",
            "params": {
                "SelectionCriteria": selection_criteria,
                "FieldNames": ["Id", "Name", "Type"],  # Get basic fields and type
                "TextCampaignFieldNames": ["PriorityGoals"],  # For TEXT_CAMPAIGN
                "DynamicTextCampaignFieldNames": ["PriorityGoals"],  # For DYNAMIC_TEXT_CAMPAIGN
                # NOTE: MobileAppCampaignFieldNames does NOT support PriorityGoals - removed to avoid error 8000
                "SmartCampaignFieldNames": ["PriorityGoals"]  # For SMART_CAMPAIGN
            }
        }
        
        campaign_goals_map = {}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.campaigns_url, json=payload, headers=self.headers, timeout=120.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "result" in data and "Campaigns" in data["result"]:
                        campaigns = data["result"]["Campaigns"]
                        
                        for campaign in campaigns:
                            campaign_id = str(campaign["Id"])
                            campaign_name = campaign.get("Name", "Unknown")
                            campaign_type = campaign.get("Type", "UNKNOWN")
                            
                            # Extract PriorityGoals based on campaign type
                            # В API PriorityGoals может отсутствовать или быть null (None),
                            # поэтому ВСЕГДА нормализуем к списку перед итерацией.
                            priority_goals = []
                            
                            def _safe_goals(container: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
                                raw = container.get(key)
                                if not raw:
                                    return []
                                if isinstance(raw, list):
                                    return raw
                                # Если почему‑то пришёл одиночный объект, тоже оборачиваем в список
                                return [raw]
                            
                            if campaign_type == "TEXT_CAMPAIGN" and "TextCampaign" in campaign:
                                priority_goals = _safe_goals(campaign["TextCampaign"], "PriorityGoals")
                            elif campaign_type == "DYNAMIC_TEXT_CAMPAIGN" and "DynamicTextCampaign" in campaign:
                                priority_goals = _safe_goals(campaign["DynamicTextCampaign"], "PriorityGoals")
                            elif campaign_type == "MOBILE_APP_CAMPAIGN" and "MobileAppCampaign" in campaign:
                                priority_goals = _safe_goals(campaign["MobileAppCampaign"], "PriorityGoals")
                            elif campaign_type == "SMART_CAMPAIGN" and "SmartCampaign" in campaign:
                                priority_goals = _safe_goals(campaign["SmartCampaign"], "PriorityGoals")
                            
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
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        Получает баланс рекламного кабинета через AccountManagement API (для Direct Pro).
        
        CRITICAL: Для Direct Pro используется метод AccountManagement вместо Clients.get.
        Баланс получается от ПРОФИЛЯ (кабинета), указанного в Client-Login заголовке.
        Если Client-Login не установлен, возвращается баланс основного кабинета токена.
        
        Returns:
            Dict с полями:
            - balance: float - баланс в валюте кабинета (из поля Amount)
            - currency: str - код валюты (RUB, USD, EUR, etc.)
            - amount: float - сумма на счете
            - amount_available_for_transfer: float - сумма доступная для перевода (если доступна)
            Или None при ошибке
        """
        # CRITICAL: Для Direct Pro используем AccountManagement API
        # Согласно документации: URL = api.direct.yandex.ru (без пути)
        # Метод AccountManagement с Action: "Get" в param
        url = "https://api.direct.yandex.ru"
        
        # CRITICAL: Log which profile we're requesting balance for
        client_login_header = self.headers.get("Client-Login", "NOT SET (main account)")
        logger.info(f"💰 Requesting balance via AccountManagement API for profile: '{client_login_header}'")
        logger.info(f"💰 Request headers: Client-Login='{client_login_header}', Authorization='Bearer ...'")
        
        # AccountManagement API требует Action: "Get" и SelectionCriteria
        # Если указан Client-Login, используем его в Logins
        # Для агентских аккаунтов: Logins содержит логин агентского аккаунта
        # AccountIDS может быть пустым (получим данные по всем рекламодателям) или содержать конкретные ID
        selection_criteria = {}
        if client_login_header != "NOT SET (main account)":
            selection_criteria["Logins"] = [client_login_header]
            # AccountIDS оставляем пустым для получения данных по всем рекламодателям агентского аккаунта
            # Или можно указать конкретные AccountIDS, если нужны данные только по определенным аккаунтам
        else:
            # Для основного аккаунта можно указать AccountIDS
            # Но если не указано, получим данные по всем аккаунтам
            pass
        
        # CRITICAL: Согласно документации, token должен быть в payload (OAuth-токен)
        # Получаем токен из заголовка Authorization
        token_from_header = self.headers.get("Authorization", "").replace("Bearer ", "")
        
        payload = {
            "method": "AccountManagement",
            "token": token_from_header,
            "param": {
                "Action": "Get",
                "SelectionCriteria": selection_criteria if selection_criteria else {}
            }
        }
        
        # CRITICAL: AccountManagement API может не требовать Authorization в заголовке, если token в payload
        # Но оставим заголовок для совместимости
        api_headers = {
            "Accept-Language": "ru",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=api_headers, timeout=30.0)
                logger.info(f"💰 Yandex AccountManagement API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"💰 Yandex AccountManagement API response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                    
                    # CRITICAL: AccountManagement API Live 4 может возвращать ошибки в ActionsResult
                    # Проверяем наличие ошибок перед обработкой данных
                    if "data" in data and "ActionsResult" in data["data"]:
                        actions_result = data["data"]["ActionsResult"]
                        if actions_result and len(actions_result) > 0:
                            for action in actions_result:
                                if "Errors" in action and action["Errors"]:
                                    for error in action["Errors"]:
                                        fault_code = error.get("FaultCode")
                                        fault_string = error.get("FaultString", "")
                                        logger.warning(f"⚠️ AccountManagement API error {fault_code}: {fault_string}")
                                        
                                        # Ошибка 515: "Shared account must be connected" - общий счет не подключен
                                        if fault_code == 515:
                                            logger.warning(f"⚠️ Profile '{action.get('Login', 'UNKNOWN')}' is a shared account that must be connected. "
                                                         f"Balance cannot be retrieved via AccountManagement API for shared accounts.")
                                            # Fallback to Clients.get
                                            logger.info("Trying Clients.get as fallback...")
                                            return await self._get_balance_fallback()
                    
                    # AccountManagement API Live 4 возвращает данные в структуре data -> Accounts
                    # (не result, а data для Live 4)
                    if "data" in data and "Accounts" in data["data"]:
                        accounts = data["data"]["Accounts"]
                    elif "result" in data and "Accounts" in data["result"]:
                        accounts = data["result"]["Accounts"]
                    else:
                        accounts = None
                    
                    if accounts and len(accounts) > 0:
                        logger.info(f"💰 Yandex AccountManagement API returned {len(accounts)} account(s)")
                        
                        if accounts and len(accounts) > 0:
                            account_data = accounts[0]
                            # CRITICAL: Log which profile's balance we received
                            profile_login = account_data.get("Login", "UNKNOWN")
                            logger.info(f"💰 Received balance for profile Login: '{profile_login}' (requested: '{client_login_header}')")
                            logger.info(f"💰 Full account data: {json.dumps(account_data, indent=2, ensure_ascii=False)}")
                            
                            # CRITICAL: Verify that we got balance for the correct profile
                            if client_login_header != "NOT SET (main account)" and profile_login != client_login_header:
                                logger.warning(f"⚠️ Profile mismatch! Requested '{client_login_header}' but got balance for '{profile_login}'")
                            
                            # CRITICAL: AccountManagement API возвращает Amount (баланс) для Direct Pro
                            amount = account_data.get("Amount")
                            currency = account_data.get("Currency", "RUB")
                            amount_available = account_data.get("AmountAvailableForTransfer")
                            
                            if amount is not None:
                                try:
                                    balance_float = float(amount) if isinstance(amount, str) else amount
                                    logger.info(f"💰 Yandex Direct balance (from AccountManagement): {balance_float} {currency} for profile '{profile_login}'")
                                    result = {
                                        "balance": balance_float,
                                        "currency": currency,
                                        "amount": balance_float
                                    }
                                    if amount_available is not None:
                                        result["amount_available_for_transfer"] = float(amount_available) if isinstance(amount_available, str) else amount_available
                                    return result
                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Failed to parse Amount value: {amount}, error: {e}")
                                    return None
                            else:
                                logger.warning(f"Amount field is not available in AccountManagement response for profile '{profile_login}'")
                                return None
                    elif "error" in data:
                        error_code = data["error"].get("error_code")
                        error_string = data["error"].get("error_string", "")
                        error_detail = data["error"].get("error_detail", "")
                        logger.warning(f"Yandex AccountManagement API error {error_code}: {error_string} - {error_detail}")
                        
                        # Если AccountManagement не доступен, пробуем Clients.get как fallback
                        if error_code == 3228 or "Direct Pro" in error_string or "AccountManagement" in error_detail:
                            logger.info("AccountManagement requires Direct Pro access, trying Clients.get as fallback...")
                            return await self._get_balance_fallback()
                        
                        return None
                    else:
                        # Если Accounts пустой, но есть ActionsResult с ошибками, уже обработано выше
                        if "data" in data and "ActionsResult" in data["data"]:
                            # Ошибки уже обработаны выше, просто возвращаем None
                            logger.warning(f"AccountManagement API returned empty Accounts array (errors in ActionsResult)")
                        else:
                            logger.warning(f"Unexpected response format from Yandex AccountManagement API: {data}")
                        # Fallback to Clients.get
                        logger.info("Trying Clients.get as fallback...")
                        return await self._get_balance_fallback()
                else:
                    logger.warning(f"Failed to fetch Yandex balance via AccountManagement: {response.status_code} - {response.text[:200]}")
                    # Fallback to Clients.get
                    logger.info("Trying Clients.get as fallback...")
                    return await self._get_balance_fallback()
            except Exception as e:
                logger.warning(f"Error fetching Yandex balance via AccountManagement: {e}")
                # Fallback to Clients.get
                logger.info("Trying Clients.get as fallback...")
                return await self._get_balance_fallback()
    
    async def _get_balance_fallback(self) -> Optional[Dict[str, Any]]:
        """
        Fallback метод для получения баланса через Clients.get (если AccountManagement недоступен).
        """
        url = "https://api.direct.yandex.com/json/v5/clients"
        payload = {
            "method": "get",
            "params": {
                "FieldNames": ["Currency", "Login"]
            }
        }
        
        client_login_header = self.headers.get("Client-Login", "NOT SET (main account)")
        logger.info(f"💰 Fallback: Requesting balance via Clients.get for profile: '{client_login_header}'")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "result" in data and "Clients" in data["result"]:
                        clients = data["result"]["Clients"]
                        
                        if clients and len(clients) > 0:
                            client_data = clients[0]
                            profile_login = client_data.get("Login", "UNKNOWN")
                            currency = client_data.get("Currency", "RUB")
                            
                            logger.warning(f"⚠️ Clients.get API does not return balance field. "
                                         f"Profile '{profile_login}' balance requires Direct Pro and AccountManagement API.")
                            
                            return None
                return None
            except Exception as e:
                logger.warning(f"Error in fallback balance fetch: {e}")
                return None
