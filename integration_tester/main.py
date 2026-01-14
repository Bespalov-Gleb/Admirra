import argparse
import logging
import sys
from .client import IntegrationApiClient
from .steps.step1_setup import run_step1
from .steps.step2_profiles import run_step2
from .steps.step3_campaigns import run_step3
from .steps.step4_goals import run_step4
from .config import TEST_API_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("IntegrationTester")

def main():
    parser = argparse.ArgumentParser(description="Test Integration Flow (4 Steps)")
    parser.add_argument("--url", default=TEST_API_URL, help=f"Backend API base URL (default: {TEST_API_URL})")
    parser.add_argument("--email", default=TEST_USER_EMAIL, help=f"User email (default: {TEST_USER_EMAIL})")
    parser.add_argument("--password", default=TEST_USER_PASSWORD, help=f"User password (default: {TEST_USER_PASSWORD})")
    parser.add_argument("--platform", default="YANDEX_DIRECT", choices=["YANDEX_DIRECT", "VK_ADS"], help="Platform")
    parser.add_argument("--token", help="Platform Access Token")
    parser.add_argument("--client-name", default="Test Project", help="Client/Project Name")
    parser.add_argument("--client-id", help="Existing Client ID (Project ID)")

    args = parser.parse_args()

    if not args.token:
        logger.error("Platform --token is required. Provide it via command line.")
        sys.exit(1)

    client = IntegrationApiClient(args.url)

    try:
        # Auth
        client.login(args.email, args.password)

        # Step 1
        integration_data = run_step1(
            client, 
            args.platform, 
            args.client_name, 
            args.token, 
            args.client_id
        )
        integration_id = integration_data["id"]

        # Step 2
        profile = run_step2(client, integration_id)
        account_id = profile.get("login") if profile else None

        # Step 3
        campaigns, selected_campaign_ids = run_step3(client, integration_id)

        # Step 4
        final_data = run_step4(
            client, 
            integration_id, 
            account_id, 
            selected_campaign_ids
        )

        logger.info("==========================================")
        logger.info("TEST SUCCESSFUL")
        logger.info(f"Integration ID: {integration_id}")
        logger.info("==========================================")

    except Exception as e:
        logger.error(f"TEST FAILED: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
