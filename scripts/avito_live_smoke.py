"""
Ручной smoke-тест Avito Ads API (без записи секретов в репозиторий).

Пример (PowerShell):
  $env:AVITO_CLIENT_ID='...'
  $env:AVITO_CLIENT_SECRET='...'
  $env:AVITO_ACCOUNT_ID='123456789'   # ID из кабинета Avito Рекламы
  python scripts/avito_live_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.avito_ads import AvitoAdsAPI  # noqa: E402


async def run() -> int:
    client_id = os.environ.get("AVITO_CLIENT_ID", "").strip()
    client_secret = os.environ.get("AVITO_CLIENT_SECRET", "").strip()
    account_id = os.environ.get("AVITO_ACCOUNT_ID", "").strip()

    if not client_id or not client_secret:
        print("FAIL: задайте AVITO_CLIENT_ID и AVITO_CLIENT_SECRET")
        return 1

    api = AvitoAdsAPI(
        credential_type="client_credentials",
        client_id=client_id,
        client_secret=client_secret,
        account_id=account_id or None,
    )

    print("1) Token exchange...")
    token = await api._get_bearer_token()
    print(f"   OK (token length={len(token)})")

    if not account_id:
        print("SKIP: задайте AVITO_ACCOUNT_ID для balance/campaigns/stats")
        return 0

    print(f"2) Balance (account {account_id})...")
    balance = await api.get_balance(account_id)
    print(f"   OK: {balance}")

    print("3) Profiles (parent + children)...")
    profiles = await api.get_profiles_or_accounts(account_id)
    print(f"   OK: {len(profiles)} profile(s)")
    for p in profiles[:5]:
        print(f"      - id={p.get('id')} name={p.get('name')} type={p.get('type')}")

    print("4) Campaigns list...")
    campaigns = await api.get_campaigns(account_id)
    print(f"   OK: {len(campaigns)} campaign(s)")
    if campaigns:
        sample = campaigns[0]
        print(
            f"      sample id={sample.get('id')} name={sample.get('name')} "
            f"status={sample.get('status')} state={sample.get('state')}"
        )

        date_to = date.today().isoformat()
        date_from = (date.today() - timedelta(days=7)).isoformat()
        print(f"5) Stats {date_from}..{date_to} for campaign {sample['id']}...")
        stats = await api.get_statistics([sample["id"]], date_from, date_to, account_id)
        print(f"   OK: {len(stats)} row(s)")
        if stats:
            row = stats[0]
            print(
                f"      sample date={row.get('date')} views={row.get('impressions')} "
                f"clicks={row.get('clicks')} spend={row.get('cost')}"
            )
    else:
        print("5) Stats: skip (no campaigns)")

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
