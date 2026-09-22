"""Detached prompt capture and revision-aware cache policy for DB-backed AI."""
from core import consumer_freshness
from core.data_requirements import DataNotReady
from backend_api.reports.direct_freshness import capture


def enabled():
    return consumer_freshness.enabled("ai")


class VerifiedText(str):
    def __new__(cls, text, proof):
        result = super().__new__(cls, text)
        result.data_revision = proof["revision"]
        return result


def revision(db, user_id, client_id, start, end):
    if not enabled():
        return None
    _, proof = capture(db, user_id, client_id, None, start, end, lambda *_: None, return_evidence=True)
    return proof["revision"]


def cache_matches(entry, revision):
    return revision is None or bool(entry and entry.get("data_revision") == revision)


def validate_publication(db, client_id, start, end, text):
    """Hold source locks through the caller's cache write + commit, not LLM IO."""
    if not enabled():
        return
    from backend_api.reports.direct_freshness import period
    first, last = period(str(start), str(end))
    proof = consumer_freshness.verify(db, [client_id], first, last)
    if getattr(text, "data_revision", None) != proof["revision"]:
        raise DataNotReady("data_changed_before_publication")
