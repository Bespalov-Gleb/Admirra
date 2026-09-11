"""Explicit bounded maintenance of expired HTML links. No token/body output."""
import argparse
import json

import sqlalchemy as sa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prune", action="store_true", help="Delete at most one batch older than retention")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("limit must be 1..1000")
    from core.database import SessionLocal
    from backend_api.reports.public_links import links, prune
    with SessionLocal.begin() as db:
        if not args.prune:
            db.execute(sa.text("SET TRANSACTION READ ONLY"))
        db.execute(sa.text("SET LOCAL statement_timeout = '5000ms'"))
        db.execute(sa.text("SET LOCAL lock_timeout = '1000ms'"))
        if args.prune:
            result = {"pruned": prune(db, args.limit)}
        else:
            result = {"active": db.scalar(sa.select(sa.func.count()).select_from(links).where(
                links.c.revoked_at.is_(None), links.c.expires_at > sa.func.clock_timestamp()))}
    print(json.dumps(result))


if __name__ == "__main__":
    main()
