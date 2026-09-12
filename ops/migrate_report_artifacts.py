"""Read-only inventory by default; explicit bounded copy/verify, never blob deletion.

Run in the release environment with its DB and private storage credentials.
No implicit sweep: --apply requires 1..20 explicit --delivery-id values.
"""
import argparse
import json
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from core import models


def inventory(factory):
    delivery = models.ReportDelivery
    with factory() as db:
        db.execute(sa.text("SET TRANSACTION READ ONLY"))
        db.execute(sa.text("SET LOCAL statement_timeout = '15s'"))
        snapshot = sa.cast(delivery.snapshot_data["_scope_client_ids"], JSONB)
        scoped = sa.or_(delivery.client_id.is_not(None), sa.and_(
            sa.func.jsonb_typeof(snapshot) == "array", snapshot != sa.cast([], JSONB)))
        row = db.execute(sa.select(
            sa.func.count().label("deliveries"),
            sa.func.count().filter(delivery.pdf_snapshot.is_not(None)).label("frozen_pdfs"),
            sa.func.count().filter(delivery.pdf_snapshot.is_not(None), scoped).label("scope_candidates"),
            sa.func.coalesce(sa.func.sum(sa.func.octet_length(delivery.pdf_snapshot)), 0).label("pdf_bytes"),
            sa.func.coalesce(sa.func.sum(sa.func.octet_length(delivery.png_snapshot)), 0).label("png_bytes"),
        )).mappings().one()
        return dict(row)


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Copy and verify explicit IDs; keep original blobs")
    parser.add_argument("--delivery-id", action="append", type=uuid.UUID, default=[])
    args = parser.parse_args(argv)
    if args.apply and not 1 <= len(args.delivery_id) <= 20:
        parser.error("--apply requires 1..20 explicit --delivery-id values")
    if args.delivery_id and not args.apply:
        parser.error("--delivery-id requires explicit --apply; default mode is aggregate inventory")
    if len(set(args.delivery_id)) != len(args.delivery_id):
        parser.error("Duplicate delivery IDs")
    return args


def main(argv=None):
    args = arguments(argv)
    from core.database import SessionLocal
    if not args.apply:
        print(json.dumps({"mode": "read-only inventory", **inventory(SessionLocal)}, sort_keys=True))
        return
    from backend_api.reports.artifacts import copy_delivery
    from backend_api.artifact_ledger import check_schema
    from core.database import engine
    from core.artifact_client import from_environment
    check_schema(engine)
    storage = from_environment()
    failed = False
    try:
        for id in args.delivery_id:
            try:
                result = copy_delivery(SessionLocal, storage, id)
                print(json.dumps({"status": "copied-and-verified", **result}, sort_keys=True))
            except Exception as exc:
                # Never print SQL parameters, public tokens, credentials or blob content.
                print(json.dumps({"delivery_id": str(id), "status": "not-attached", "error_type": type(exc).__name__}))
                failed = True
    finally:
        storage.close()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
