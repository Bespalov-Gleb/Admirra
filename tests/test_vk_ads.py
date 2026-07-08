import unittest
from unittest.mock import patch

import httpx

from automation.vk_ads import VKAdsAPI, vk_agency_exchange_hints


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload or {"items": []}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._payload


class _FakeAsyncClient:
    responses = []
    calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, **kwargs):
        self.__class__.calls.append((url, kwargs))
        return self.__class__.responses.pop(0)


class VKAdsStatisticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _FakeAsyncClient.calls = []
        _FakeAsyncClient.responses = []

    async def test_statistics_batches_campaign_ids_and_does_not_send_client_id(self):
        campaigns = [
            {"id": str(index), "name": f"Campaign {index}"}
            for index in range(1, 206)
        ]
        _FakeAsyncClient.responses = [_FakeResponse(), _FakeResponse()]

        api = VKAdsAPI("token", "123456", send_client_id=True)
        with patch("automation.vk_ads.httpx.AsyncClient", _FakeAsyncClient), patch(
            "automation.vk_ads.asyncio.sleep",
            return_value=None,
        ):
            rows = await api.get_statistics(
                "2026-06-01",
                "2026-06-10",
                campaigns=campaigns,
            )

        self.assertEqual(rows, [])
        self.assertEqual(len(_FakeAsyncClient.calls), 2)
        first_params = _FakeAsyncClient.calls[0][1]["params"]
        second_params = _FakeAsyncClient.calls[1][1]["params"]
        self.assertEqual(len(first_params["id"].split(",")), 200)
        self.assertEqual(len(second_params["id"].split(",")), 5)
        self.assertNotIn("client_id", first_params)
        self.assertNotIn("client_id", second_params)

    async def test_statistics_raises_on_invalid_request_instead_of_silent_success(self):
        _FakeAsyncClient.responses = [
            _FakeResponse(status_code=400, text="ERR_WRONG_PARAMETER")
        ]
        api = VKAdsAPI("token")

        with patch("automation.vk_ads.httpx.AsyncClient", _FakeAsyncClient):
            with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
                await api.get_statistics(
                    "2026-06-01",
                    "2026-06-10",
                    campaigns=[{"id": "42", "name": "Lead campaign"}],
                )

    def test_statistics_parser_uses_string_campaign_ids(self):
        api = VKAdsAPI("token")
        rows = api._parse_response(
            {
                "items": [
                    {
                        "id": 42,
                        "rows": [
                            {
                                "date": "2026-06-01",
                                "base": {
                                    "shows": 100,
                                    "clicks": 10,
                                    "spent": 500,
                                    "vk": {"goals": 2, "cpa": 250},
                                },
                            }
                        ],
                    }
                ]
            },
            {"42": "Lead campaign"},
        )

        self.assertEqual(rows[0]["campaign_name"], "Lead campaign")
        self.assertEqual(rows[0]["conversions"], 2)
        self.assertEqual(rows[0]["cpa"], 250)

    def test_nested_agency_client_profile_uses_username_as_login(self):
        profile = VKAdsAPI._profile_from_client_item(
            {
                "user": {
                    "id": 13034808,
                    "username": "vkads_355780568@vk@1241124",
                    "status": "active",
                    "additional_info": {"client_name": "X-Fit Сормово"},
                }
            },
            "agency_client",
        )

        self.assertEqual(profile["id"], "13034808")
        self.assertEqual(profile["login"], "vkads_355780568@vk@1241124")
        self.assertEqual(profile["type"], "agency_client")
        self.assertIn("X-Fit Сормово", profile["name"])

    def test_same_numeric_vk_profile_id_is_tried_before_cabinet_fallback(self):
        name, uid, cabinet_only = vk_agency_exchange_hints("13034808", "13034808")

        self.assertIsNone(name)
        self.assertEqual(uid, "13034808")
        self.assertEqual(cabinet_only, "13034808")


if __name__ == "__main__":
    unittest.main()
