"""Strict read-only VK hierarchy transport, separate from legacy UI fallbacks.

A failed page/chunk is never a successful partial catalog or zero statistics.
Uses the established VK endpoint/filter contract; does not rotate credentials.
"""
from automation.ads_sync_contract import (
    MAX_BYTES, IncompleteAdsSnapshot, bounded, identifier, items, vk_statistics,
)
from automation.provider_transport import provider_client


PAGE_SIZE = 200
MAX_PAGES = 100


def payload(response):
    response.raise_for_status()
    if len(response.content) > MAX_BYTES:
        raise IncompleteAdsSnapshot("VK hierarchy response exceeds byte budget")
    data = response.json()
    if not isinstance(data, dict) or data.get("error"):
        raise IncompleteAdsSnapshot("VK hierarchy API error")
    return data


async def catalog(api, parent_ids, *, banners=False):
    parents = list(dict.fromkeys(identifier(value) for value in parent_ids))
    endpoint = "banners" if banners else "ad_groups"
    parent_field = "ad_group_id" if banners else "ad_plan_id"
    result, seen = [], set()
    async with provider_client("vk") as client:
        for first in range(0, len(parents), PAGE_SIZE):
            chunk = parents[first:first + PAGE_SIZE]
            offset, expected_count = 0, None
            for _ in range(MAX_PAGES):
                params = {f"_{parent_field}__in": ",".join(chunk),
                          "fields": f"id,name,{parent_field}", "limit": PAGE_SIZE, "offset": offset}
                if api.account_id and api.send_client_id:
                    params["client_id"] = api.account_id
                await api._throttle()
                data = payload(await client.get(f"{api.base_url}/{endpoint}.json",
                    params=params, headers=api.headers, timeout=30.0))
                page = items(data, "items")
                if len(page) > PAGE_SIZE:
                    raise IncompleteAdsSnapshot("VK hierarchy oversized page")
                if "count" in data:
                    count = data["count"]
                    if type(count) is not int or count < 0 or (expected_count is not None and count != expected_count):
                        raise IncompleteAdsSnapshot("VK hierarchy catalog count changed")
                    expected_count = count
                for row in page:
                    key = identifier(row.get("id"))
                    if identifier(row.get(parent_field)) not in chunk or key in seen:
                        raise IncompleteAdsSnapshot("VK hierarchy catalog scope/duplicate error")
                    seen.add(key)
                    result.append(row)
                bounded(result)
                offset += len(page)
                if expected_count is not None:
                    if offset > expected_count or (not page and offset < expected_count):
                        raise IncompleteAdsSnapshot("VK hierarchy catalog truncated")
                    if offset == expected_count:
                        break
                elif len(page) < PAGE_SIZE:
                    break
            else:
                raise IncompleteAdsSnapshot("VK hierarchy catalog page budget exceeded")
    return result


async def statistics(api, level, object_ids, start, end):
    if level not in ("ad_groups", "banners"):
        raise ValueError("Unsupported VK hierarchy level")
    ids = list(dict.fromkeys(identifier(value) for value in object_ids))
    result, seen = [], set()
    async with provider_client("vk") as client:
        for date_from, date_to in api._split_date_range(start, end, 90):
            for first in range(0, len(ids), PAGE_SIZE):
                chunk = ids[first:first + PAGE_SIZE]
                # Statistics is scoped by token and object IDs, never client_id.
                params = dict(date_from=date_from, date_to=date_to, id=",".join(chunk), metrics="base")
                await api._throttle()
                data = payload(await client.get(f"{api.base_url}/statistics/{level}/day.json",
                    params=params, headers=api.headers, timeout=120.0))
                for row in vk_statistics(data, {key: key for key in chunk}, date_from, date_to, set(chunk)):
                    key = (row["date"], row["campaign_id"])
                    if key in seen:
                        raise IncompleteAdsSnapshot("VK hierarchy duplicate daily statistic")
                    seen.add(key)
                    result.append(dict(row, object_id=row["campaign_id"]))
                bounded(result)
    return result
