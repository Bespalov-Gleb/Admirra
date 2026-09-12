"""Copy/verify legacy report snapshots without deleting or regenerating bytes."""
import hashlib
from io import BytesIO
import uuid

from backend_api import artifact_ledger as ledger
from backend_api.artifact_workflow import persist
from backend_api.artifact_response import ArtifactResponse
from backend_api.reports.public_links import authorize
from core import models
from core.runtime import env_bool


def scope_of(delivery):
    scope = (delivery.snapshot_data or {}).get("_scope_client_ids")
    if scope:
        return sorted({str(uuid.UUID(str(id))) for id in scope})
    if delivery.client_id:
        return [str(delivery.client_id)]
    # Current folder membership cannot prove historical snapshot scope.
    raise ValueError("Legacy aggregate snapshot needs verified historical scope")


def _fingerprint(delivery):
    return (scope_of(delivery), {format: hashlib.sha256(getattr(delivery, format + "_snapshot")).hexdigest()
        for format in ("pdf", "png") if getattr(delivery, format + "_snapshot")})


def copy_delivery(factory, storage, delivery_id):
    with factory() as db:
        delivery = db.query(models.ReportDelivery).filter(models.ReportDelivery.id == delivery_id).first()
        if not delivery or not delivery.pdf_snapshot:
            raise ValueError("A frozen PDF is required")
        creator_id = delivery.user_id
        before = _fingerprint(delivery)
        scope, hashes = before
        authorize(db, creator_id, scope)
        content = {format: bytes(getattr(delivery, format + "_snapshot")) for format in hashes}
    copied = {}
    scope_hash = hashlib.sha256(",".join(scope).encode()).hexdigest()
    for format, data in content.items():
        copied[format] = persist(factory, storage, creator_id, scope, "report_" + format, BytesIO(data),
            f"delivery:{delivery_id}:{format}:{hashes[format]}:{scope_hash}")
    with factory.begin() as db:
        current = db.query(models.ReportDelivery).filter(models.ReportDelivery.id == delivery_id,
            models.ReportDelivery.user_id == creator_id).with_for_update().first()
        if current is None or _fingerprint(current) != before:
            raise ledger.ArtifactConflict()
        for format, row in copied.items():
            ledger.attach_report(db, delivery_id, creator_id, format, row["id"], hashes[format])
        db.execute(ledger.references.delete().where(ledger.references.c.delivery_id == delivery_id,
            ledger.references.c.format.not_in(list(copied))))
    return {"delivery_id": str(delivery_id), "formats": sorted(copied)}


def download_if_migrated(db, delivery, format):
    """Changed draft bytes never reuse stale bindings; source blobs stay intact."""
    if not env_bool("SHARED_REPORT_ARTIFACTS", False):
        return None
    raw = getattr(delivery, format + "_snapshot")
    if not raw:
        return None
    row = ledger.linked_report(db, delivery.id, delivery.user_id, format, hashlib.sha256(raw).hexdigest())
    if row is None:
        return None
    info = ledger.descriptor(row)
    filename = f"report_{delivery.start_date}_{delivery.end_date}.{format}"
    db.rollback()  # release request connection before remote IO/slow client
    return ArtifactResponse(info, ledger.MIME[row["kind"]], filename, inline=True)
