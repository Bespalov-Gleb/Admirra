import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from backend_api import integrations


class VKClientLinkSecurityTests(unittest.TestCase):
    def test_state_is_signed_and_tampering_is_rejected(self):
        cfg = SimpleNamespace(security=SimpleNamespace(secret_key="state-test-secret", encryption_key=""))
        with patch.object(integrations, "cfg", cfg):
            state = integrations._sign_vk_client_link_state("one-time-token")
            self.assertEqual(integrations._parse_vk_client_link_state(state), "one-time-token")
            self.assertIsNone(integrations._parse_vk_client_link_state(state + "x"))
            self.assertIsNone(integrations._parse_vk_client_link_state("other-token." + state.split(".", 1)[1]))

    def test_client_url_uses_only_read_scopes_and_registered_callback(self):
        cfg = SimpleNamespace(security=SimpleNamespace(secret_key="state-test-secret", encryption_key=""))
        with patch.object(integrations, "cfg", cfg), patch.object(integrations, "VK_CLIENT_ID", "vk-ads-client"), patch.object(
            integrations, "_vk_client_link_redirect_uri", return_value="https://admirra.ru/auth/vk/callback"
        ):
            url = integrations._build_vk_client_link_url("one-time-token")

        parsed = parse_qs(urlparse(url).query)
        self.assertEqual(parsed["action"], ["oauth2"])
        self.assertEqual(parsed["response_type"], ["code"])
        self.assertEqual(parsed["scope"], ["read_ads,read_payments"])
        self.assertNotIn("create_ads", parsed["scope"][0])
        self.assertEqual(parsed["redirect_uri"], ["https://admirra.ru/auth/vk/callback"])
        self.assertTrue(integrations.is_vk_client_link_state(parsed["state"][0]))

    def test_expired_link_clears_reusable_token(self):
        integration = SimpleNamespace(
            connection_status="awaiting_auth",
            link_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            link_token="encrypted",
            link_token_hash="hash",
        )

        self.assertTrue(integrations._expire_vk_client_link_if_needed(integration))
        self.assertEqual(integration.connection_status, "link_expired")
        self.assertIsNone(integration.link_token)
        self.assertIsNone(integration.link_token_hash)


if __name__ == "__main__":
    unittest.main()
