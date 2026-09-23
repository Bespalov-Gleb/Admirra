"""Fail-closed contracts for complete advertising snapshots (not UI previews)."""
from datetime import date
from decimal import Decimal, InvalidOperation
import json

MAX_ROWS = 100_000
MAX_BYTES = 32 * 1024 * 1024


class IncompleteAdsSnapshot(ValueError):
    pass


def number(value, *, integer=False, missing=False):
    if missing and value in (None, "--", "-"):
        return 0
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise IncompleteAdsSnapshot("Invalid advertising metric") from None
    if not result.is_finite() or result < 0 or result >= Decimal("1e18"):
        raise IncompleteAdsSnapshot("Advertising metric outside storage limits")
    if integer and result != result.to_integral_value():
        raise IncompleteAdsSnapshot("Fractional advertising count cannot be stored as an integer")
    return int(result) if integer else result


def bounded(value):
    if len(value) > MAX_ROWS or len(json.dumps(value, default=str).encode()) > MAX_BYTES:
        raise IncompleteAdsSnapshot("Advertising snapshot too large; request a shorter window")
    return value


def items(payload, key):
    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
        raise IncompleteAdsSnapshot("Advertising response has no explicit collection")
    if any(not isinstance(row, dict) for row in payload[key]):
        raise IncompleteAdsSnapshot("Advertising collection contains a malformed row")
    return bounded(payload[key])


def identifier(value):
    if value is None or isinstance(value, bool) or not str(value).isdigit():
        raise IncompleteAdsSnapshot("Advertising row has no stable numeric identifier")
    return str(value)


def direct_tsv(text, level):
    if len(text.encode()) > MAX_BYTES:
        raise IncompleteAdsSnapshot("Direct report exceeds snapshot byte budget")
    fields = ["Date", "CampaignId", "CampaignName", "Impressions", "Clicks", "Cost", "Conversions"]
    if level == "group":
        fields[3:3] = ["AdGroupId", "AdGroupName"]
    elif level == "ad":
        fields[3:3] = ["AdGroupId", "AdId"]
    elif level == "keyword":
        fields.insert(2, "Criteria")
    expected = len(fields)
    result, header, total = [], False, None
    for line in text.splitlines():
        if not line.strip():
            continue
        columns = line.split("\t")
        if columns[0] == "Date":
            if columns != fields:
                raise IncompleteAdsSnapshot("Unexpected Direct report columns")
            header = True
            continue
        if columns[0].startswith("Total rows:"):
            total = int(line.removeprefix("Total rows:").strip())
            continue
        if not header and not result and len(columns) == 1:
            # Reports may include their generated name before the column header.
            # Direct wraps this metadata row in quotes in real TSV responses.
            # Do not strip quotes from campaign names/data or relax row coverage.
            title = line[1:-1] if line.startswith('"') and line.endswith('"') else line
            if title.startswith("AgencyStats_"):
                continue
        if len(columns) != expected:
            raise IncompleteAdsSnapshot("Truncated Direct report row")
        date.fromisoformat(columns[0])
        offset = 3 if level == "campaign" else 5 if level in {"group", "ad"} else 4
        row = dict(date=columns[0], campaign_id=identifier(columns[1]),
            campaign_name=columns[3] if level == "keyword" else columns[2],
            impressions=number(columns[offset], integer=True), clicks=number(columns[offset + 1], integer=True),
            cost=number(columns[offset + 2]) / 1_000_000,
            conversions=number(columns[offset + 3], integer=True, missing=True))
        if level == "group":
            # Campaign Wizard deliberately hides BOTH fields, sometimes in
            # several rows for one campaign/day. Preserve metrics, not fake IDs.
            # https://yandex.ru/dev/direct/doc/ru/report-format
            hidden = columns[3] == "--" and columns[4] == "--"
            row.update(group_id=None if hidden else identifier(columns[3]), name=columns[4])
        if level == "ad":
            row.update(group_id=identifier(columns[3]), ad_id=identifier(columns[4]))
        if level == "keyword":
            row["name"] = columns[2]
        result.append(row)
        if len(result) > MAX_ROWS:
            raise IncompleteAdsSnapshot("Direct report exceeds row budget")
    if (not header and not result) or (total is not None and total != len(result)):
        raise IncompleteAdsSnapshot("Direct report coverage is unconfirmed")
    if level in {"group", "keyword"}:
        # Validate the provider's ORIGINAL row count before coalescing opaque
        # groups into the only available storage identity: campaign + day.
        grouped, opaque = [], {}
        for row in result:
            if level == 'group' and row['group_id'] is not None:
                grouped.append(row)
                continue
            # Criteria is implicitly grouped by CriteriaId by Direct; several
            # criteria (e.g. autotargeting) can have identical displayed text.
            # Our keyword table stores that text, not the hidden criteria ID.
            key = row['campaign_id'], row['date'], row.get('name')
            if key not in opaque:
                opaque[key] = row
                grouped.append(row)
            else:
                for metric in ('impressions', 'clicks', 'cost', 'conversions'):
                    opaque[key][metric] += row[metric]
        result = grouped
    return result


async def direct_catalog(api):
    from automation.provider_transport import provider_client
    from automation.request_queue import get_api_limiter
    result, seen, offset = [], set(), 0
    async with provider_client("direct") as client:
        while True:
            await get_api_limiter("direct").acquire()
            response = await client.post(api.campaigns_url, headers=api.headers, timeout=120.0,
                json={"method": "get", "params": {"SelectionCriteria": {
                    "States": ["ON", "OFF", "SUSPENDED", "ENDED", "CONVERTED", "ARCHIVED"]},
                    "FieldNames": ["Id", "Name", "Status", "State", "StatusPayment", "Type"],
                    "Page": {"Limit": 1000, "Offset": offset}}})
            if response.status_code in (401, 403):
                raise PermissionError(f"Direct catalog HTTP {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("error"):
                code = data["error"].get("error_code")
                if code == 3228:
                    # Catalogue metadata unavailable without Direct Pro. The
                    # complete date-scoped campaign report remains mandatory;
                    # discover campaign IDs from it without a 10-year fallback.
                    return None
                if code in (53, 54):
                    raise PermissionError("Direct catalog authorization expired (401)")
                raise IncompleteAdsSnapshot("Direct catalog API error")
            body = data.get("result") if isinstance(data, dict) else None
            page = items(body, "Campaigns")
            for row in page:
                key = identifier(row.get("Id"))
                if key in seen:
                    raise IncompleteAdsSnapshot("Direct catalog repeated a page or identifier")
                seen.add(key)
                result.append(dict(id=key, name=row.get("Name") or f"Campaign {key}",
                    state=row.get("State"), status=row.get("Status"), status_payment=row.get("StatusPayment")))
            bounded(result)
            next_offset = body.get("LimitedBy")
            if next_offset is None:
                return result
            if not page or type(next_offset) is not int or next_offset <= offset:
                raise IncompleteAdsSnapshot("Direct catalog pagination did not advance")
            offset = next_offset


def vk_statistics(payload, names, start, end, allowed):
    result = []
    for item in items(payload, "items"):
        campaign = identifier(item.get("id"))
        if campaign not in allowed:
            raise IncompleteAdsSnapshot("VK returned another campaign's statistics")
        for row in items(item, "rows"):
            day = str(row.get("date", ""))
            date.fromisoformat(day)
            if not start <= day <= end or not isinstance(row.get("base"), dict):
                raise IncompleteAdsSnapshot("VK statistics window or metrics are incomplete")
            base = row["base"]
            vk = base.get("vk", {})
            if not isinstance(vk, dict):
                raise IncompleteAdsSnapshot("Malformed VK objective metrics")
            clicks, cost = number(base.get("clicks"), integer=True), number(base.get("spent"))
            conversions = number(vk.get("goals", base.get("goals", 0)), integer=True)
            cpc = number(base["cpc"]) if base.get("cpc") is not None else cost / clicks if clicks else None
            raw_cpa = vk.get("cpa") if vk.get("cpa") is not None else base.get("cpa")
            cpa = number(raw_cpa) if raw_cpa is not None else None
            if not cpa and conversions:
                cpa = cost / conversions
            result.append(dict(campaign_id=campaign, campaign_name=names[campaign], date=day,
                impressions=number(base.get("shows"), integer=True), clicks=clicks, cost=cost,
                conversions=conversions, cpc=cpc, cpa=cpa))
    return bounded(result)


def avito_entity(entity, *, optional_data=False):
    identifier(entity.get("id"))
    if optional_data and "data" not in entity:
        return
    for row in items(entity, "data"):
        from automation.avito_ads import _parse_stats_date
        if not _parse_stats_date(row.get("timestamp")):
            raise IncompleteAdsSnapshot("Avito statistics date missing")
        number(row.get("views"), integer=True)
        number(row.get("clicks"), integer=True)
        number(row.get("spend"))
