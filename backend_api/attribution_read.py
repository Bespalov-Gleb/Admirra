"""Short SQL snapshots around live campaign attribution, never across HTTP.

These plans are internal, credential-bearing values, not response DTOs. Only
read handlers may use this boundary: it deliberately refuses pending writes.
Validation rejects a late answer after settings/scope changed; it does not
claim atomicity between provider data and the locally synchronized stats.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import SimpleNamespace

from fastapi import HTTPException

from backend_api.read_snapshot import begin_read_snapshot
from core import models


class AttributionChanged(HTTPException):
    def __init__(self):
        super().__init__(409, "Настройки проекта изменились во время загрузки. Обновите данные.")


class IntegrationSnapshot(SimpleNamespace):
    def __repr__(self):
        return "<AttributionIntegration>"


# Do not include balance/last_sync_at/status timestamps: an ordinary sync must
# not invalidate an unchanged attribution contract. Never load ORM relations.
_INTEGRATION_FIELDS = (
    "id", "client_id", "platform", "access_token", "account_id", "is_agency",
    "agency_client_login", "oauth_app", "connection_status", "selected_counters",
    "selected_goals", "primary_goal_id", "utm_source", "metrika_access_token",
    "metrika_account_id",
)


def _require_read_only(db):
    if db.new or db.dirty or db.deleted:
        raise RuntimeError("Attribution read cannot discard pending changes")


@dataclass(frozen=True, repr=False)
class AttributionPlan:
    projects: tuple = field(repr=False)
    integrations: tuple = field(repr=False)
    campaigns: tuple = field(repr=False)

    def __repr__(self):
        return "<AttributionPlan>"

    def groups(self):
        grouped = {}
        for cid, iid, name, external in self.campaigns:
            grouped.setdefault(iid, []).append(SimpleNamespace(id=cid, integration_id=iid,
                                                               name=name, external_id=external))
        for values in self.integrations:
            integration = IntegrationSnapshot(**dict(zip(_INTEGRATION_FIELDS, values)))
            yield integration, tuple(grouped.get(integration.id, ()))


def _load(db, client_ids, platform, campaign_ids, user_id):
    if user_id is not None:
        from backend_api.access_control import get_accessible_client_ids
        user = db.query(models.User).populate_existing().filter(models.User.id == user_id).first()
        if not user or not user.is_active or not set(client_ids).issubset(get_accessible_client_ids(db, user)):
            raise HTTPException(403, "Доступ к проекту изменился")
    projects = tuple(db.query(models.Client.id, models.Client.owner_id, models.Client.folder_id)
                     .filter(models.Client.id.in_(client_ids)).order_by(models.Client.id).all())
    query = db.query(*(getattr(models.Integration, key) for key in _INTEGRATION_FIELDS)).filter(
        models.Integration.client_id.in_(client_ids), models.Integration.platform == platform)
    if campaign_ids:
        query = query.filter(models.Integration.id.in_(db.query(models.Campaign.integration_id)
                             .filter(models.Campaign.id.in_(campaign_ids))))
    integrations = tuple(query.order_by(models.Integration.id).all())
    campaign_query = db.query(models.Campaign.id, models.Campaign.integration_id,
                              models.Campaign.name, models.Campaign.external_id).filter(
        models.Campaign.integration_id.in_([row.id for row in integrations]))
    if campaign_ids:
        campaign_query = campaign_query.filter(models.Campaign.id.in_(campaign_ids))
    campaigns = tuple(campaign_query.order_by(models.Campaign.id).all())
    return AttributionPlan(projects, integrations, campaigns)


def _snapshot(db, client_ids, platform, campaign_ids, user_id):
    _require_read_only(db)
    try:
        # Release the auth/prior read, use one coherent SQL-only preparation,
        # then release it before handing plain values to the provider caller.
        db.rollback()
        begin_read_snapshot(db)
        return _load(db, client_ids, platform, campaign_ids, user_id)
    finally:
        db.rollback()


@contextmanager
def attribution_read(db, client_ids, platform, campaign_ids=None, *, user_id=None):
    plan = _snapshot(db, client_ids, platform, campaign_ids, user_id)
    try:
        yield plan
        # Re-read columns, not stale objects from the Session identity map.
        if _snapshot(db, client_ids, platform, campaign_ids, user_id) != plan:
            raise AttributionChanged()
    finally:
        # Also on provider failure and asyncio cancellation. Refuse to silently
        # discard writes if a future caller violates this read-only contract.
        _require_read_only(db)
        db.rollback()
