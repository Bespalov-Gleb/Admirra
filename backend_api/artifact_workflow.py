"""Short database transactions around long external storage IO."""
import hashlib

from backend_api import artifact_ledger as ledger
from core.artifact_storage import MAX_BYTES, CHUNK_BYTES, ObjectMissing, StorageUnavailable


def persist(factory, storage, creator_id, scope_ids, kind, source, request_key):
    """Source must be a private seekable file/BytesIO, not an unbounded URL."""
    source.seek(0)
    size, digest = 0, hashlib.sha256()
    while chunk := source.read(CHUNK_BYTES):
        size += len(chunk)
        if size > MAX_BYTES:
            raise ValueError("Artifact exceeds size limit")
        digest.update(chunk)
    source.seek(0)
    with factory.begin() as db:
        reserved = ledger.reserve(db, creator_id, scope_ids, kind, size, digest.hexdigest(), request_key)
        info, generation = ledger.descriptor(reserved), reserved["generation"]
        ready = reserved["state"] == "ready"
    if ready:
        # Idempotent success must not hide a missing/corrupted storage object.
        try:
            if storage.stat(info.key) != info:
                raise StorageUnavailable()
        except ObjectMissing:
            raise StorageUnavailable() from None
        return reserved
    actual = storage.put(info, iter(lambda: source.read(CHUNK_BYTES), b""))
    with factory.begin() as db:
        return ledger.finalize(db, reserved["id"], creator_id, generation, actual)


def cleanup(factory, storage, limit=50):
    with factory.begin() as db:
        candidates = ledger.claim_cleanup(db, limit)
    finished = 0
    for row in candidates:
        # Storage delete leaves a durable tombstone. If the process dies after
        # this call, the lease retry repeats the same idempotent operation.
        storage.delete(str(row["id"]))
        with factory.begin() as db:
            ledger.finish_cleanup(db, row["id"], row["generation"])
        finished += 1
    return finished
