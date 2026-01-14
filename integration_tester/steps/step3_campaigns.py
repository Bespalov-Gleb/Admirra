import logging
from ..client import IntegrationApiClient

logger = logging.getLogger(__name__)

def run_step3(client: IntegrationApiClient, integration_id: str):
    """
    Simulates Step 3: Discover campaigns.
    """
    logger.info(f"--- Step 3: Discovering campaigns for integration {integration_id} ---")
    
    # POST /integrations/{id}/discover-campaigns
    campaigns = client.post(f"/integrations/{integration_id}/discover-campaigns")
    
    logger.info(f"Discovered {len(campaigns)} campaigns.")
    for c in campaigns:
        logger.info(f"  - [{c.get('id')}] {c.get('name')} (External ID: {c.get('external_id')})")
    
    # Normally we would filter them here. 
    # For testing, we'll mark all of them as "to be activated"
    selected_ids = [c.get("id") for c in campaigns]
    
    logger.info(f"Selected {len(selected_ids)} campaigns for activation.")
    
    return campaigns, selected_ids
