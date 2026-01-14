import logging
from ..client import IntegrationApiClient

logger = logging.getLogger(__name__)

def run_step1(client: IntegrationApiClient, platform: str, client_name: str, access_token: str, client_id_proj: str = None):
    """
    Simulates Step 1: Initial integration setup.
    If client_id_proj is provided, uses existing project.
    Otherwise, a new project with client_name will be created by the backend.
    """
    logger.info(f"--- Step 1: Setting up {platform} integration ---")
    
    payload = {
        "platform": platform,
        "client_name": client_name,
        "access_token": access_token
    }
    
    if client_id_proj:
        payload["client_id"] = client_id_proj

    # POST /integrations/
    integration_data = client.post("/integrations/", payload)
    
    integration_id = integration_data.get("id")
    logger.info(f"Step 1 Successful. Integration ID: {integration_id}")
    
    return integration_data
