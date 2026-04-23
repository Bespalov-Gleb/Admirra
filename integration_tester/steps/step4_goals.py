import logging
from ..client import IntegrationApiClient

logger = logging.getLogger(__name__)

def run_step4(client: IntegrationApiClient, integration_id: str, account_id: str, selected_campaign_ids: list):
    """
    Simulates Step 4: Fetch goals and Finalize.
    """
    logger.info(f"--- Step 4: Goals and Finalization for integration {integration_id} ---")
    
    # 1. Fetch Goals
    # GET /integrations/{id}/goals?account_id={accountId}
    goals = client.get(f"/integrations/{integration_id}/goals", params={"account_id": account_id})
    
    if not goals:
        logger.warning("No goals found. Proceeding with empty goals.")
    else:
        logger.info(f"Found {len(goals)} goals.")
        for idx, g in enumerate(goals):
            logger.info(f"  [{idx}] {g.get('name')} (ID: {g.get('id')})")

    # 2. Finalize Connection
    logger.info("Finalizing connection...")
    
    # 2a. Activate campaigns
    for c_id in selected_campaign_ids:
        client.patch(f"/campaigns/{c_id}", {"is_active": True})
    
    # 2b. Save goals
    primary_goal_id = goals[0].get("id") if goals else None
    selected_goal_ids = [g.get("id") for g in goals]
    
    final_data = client.patch(f"/integrations/{integration_id}", {
        "selected_goals": selected_goal_ids,
        "primary_goal_id": primary_goal_id
    })
    
    logger.info("Step 4 Successful. Integration Finalized.")
    return final_data
