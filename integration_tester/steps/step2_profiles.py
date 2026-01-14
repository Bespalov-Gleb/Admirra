import logging
from ..client import IntegrationApiClient

logger = logging.getLogger(__name__)

def run_step2(client: IntegrationApiClient, integration_id: str):
    """
    Simulates Step 2: Fetch and select profile.
    """
    logger.info(f"--- Step 2: Fetching profiles for integration {integration_id} ---")
    
    # GET /integrations/{id}/profiles
    profiles = client.get(f"/integrations/{integration_id}/profiles")
    
    if not profiles:
        logger.warning("No profiles found. Backend might have auto-detected account.")
        return None

    logger.info(f"Found {len(profiles)} profiles.")
    for idx, p in enumerate(profiles):
        login_display = p.get('login') or 'Unknown'
        name_display = p.get('name') or 'Unnamed'
        logger.info(f"  [{idx}] {name_display} (Login: {login_display})")

    # For testing, we select the first profile
    selected_profile = profiles[0]
    login = selected_profile.get("login")
    
    logger.info(f"Selecting profile: {login}")
    
    # PATCH /integrations/{id}
    client.patch(f"/integrations/{integration_id}", {
        "account_id": login,
        "agency_client_login": login
    })
    
    logger.info("Step 2 Successful.")
    return selected_profile
