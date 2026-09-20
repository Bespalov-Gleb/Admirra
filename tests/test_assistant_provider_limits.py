from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from ai.assistant.yandex_client import AiYandexClient


class AssistantProviderLimitsTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_yandex_tool_paths_use_shared_transport(self):
        access = SimpleNamespace(access_token=lambda: "synthetic", client_login=None)
        client = AiYandexClient(access)
        response = SimpleNamespace(status_code=200, text="CampaignId\tClicks\n1\t5\n",
                                   json=lambda: {"result": {"ok": True}})
        transport = SimpleNamespace(post=AsyncMock(return_value=response), get=AsyncMock(return_value=response))
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=transport)
        manager.__aexit__ = AsyncMock(return_value=False)
        with patch("ai.assistant.yandex_client.provider_client", return_value=manager) as factory:
            await client.direct_call("campaigns", "get", {})
            await client.direct_report({})
            await client.metrika_get("/stat/v1/data", {})
        self.assertEqual([call.args[0] for call in factory.call_args_list], ["direct", "direct", "metrica"])
