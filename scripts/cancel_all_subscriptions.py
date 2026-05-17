#!/usr/bin/env python3
"""
Массовая отмена рекуррентных подписок CloudPayments и синхронизация БД.

Запуск из каталога trafic_agent:
  python -m scripts.cancel_all_subscriptions
  python -m scripts.cancel_all_subscriptions --db-only

В Docker:
  docker compose exec backend python -m scripts.cancel_all_subscriptions
  docker compose exec backend python -m scripts.cancel_all_subscriptions --db-only

Только БД (без вызова API CloudPayments):
  docker compose exec db psql -U postgres -d saas_project -c "UPDATE subscriptions SET status = 'CANCELED', cancel_at_period_end = false, updated_at = NOW() WHERE status IN ('ACTIVE', 'TRIAL', 'PAST_DUE'); UPDATE users SET is_subscribed = false;"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from backend_api.services.cloudpayments import CloudPaymentsService
from core import models
from core.database import SessionLocal


def _cancel_all_in_db(db: Session) -> tuple[int, int]:
    subs = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.status.in_(
                [
                    models.SubscriptionStatus.ACTIVE,
                    models.SubscriptionStatus.TRIAL,
                    models.SubscriptionStatus.PAST_DUE,
                ]
            )
        )
        .all()
    )
    user_ids = {s.user_id for s in subs}
    for sub in subs:
        sub.status = models.SubscriptionStatus.CANCELED
        sub.cancel_at_period_end = False
    if user_ids:
        db.query(models.User).filter(models.User.id.in_(user_ids)).update(
            {models.User.is_subscribed: False},
            synchronize_session=False,
        )
    db.commit()
    return len(subs), len(user_ids)


async def _cancel_in_cloudpayments(db: Session) -> tuple[int, int, int]:
    rows = (
        db.query(models.Subscription)
        .filter(models.Subscription.cloudpayments_subscription_id.isnot(None))
        .filter(models.Subscription.cloudpayments_subscription_id != "")
        .filter(
            models.Subscription.status.in_(
                [
                    models.SubscriptionStatus.ACTIVE,
                    models.SubscriptionStatus.PAST_DUE,
                ]
            )
        )
        .all()
    )
    ok = 0
    failed = 0
    for sub in rows:
        cp_id = (sub.cloudpayments_subscription_id or "").strip()
        if not cp_id:
            continue
        try:
            result = await CloudPaymentsService.cancel_subscription(cp_id)
            if isinstance(result, dict) and result.get("Success") is False:
                print(f"  FAIL {cp_id}: {result.get('Message') or result}")
                failed += 1
                continue
            ok += 1
            print(f"  OK   {cp_id} (user {sub.user_id})")
        except Exception as exc:
            print(f"  ERR  {cp_id}: {exc}")
            failed += 1

    subs_count, users_count = _cancel_all_in_db(db)
    return ok, failed, subs_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Отменить все подписки (CloudPayments + БД)")
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Только обновить БД, без вызовов CloudPayments API",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.db_only:
            subs_count, users_count = _cancel_all_in_db(db)
            print(f"БД: подписок помечено CANCELED={subs_count}, пользователей is_subscribed=false={users_count}")
            return

        ok, failed, subs_count = asyncio.run(_cancel_in_cloudpayments(db))
        print(f"CloudPayments: успешно={ok}, ошибок={failed}")
        print(f"БД: подписок CANCELED={subs_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
