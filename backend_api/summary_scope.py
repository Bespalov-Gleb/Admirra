"""Short-lived integration metadata for one authorized summary request.

This is not a cross-request cache: no TTL, credentials, ORM entities or session
registry. Callers load it AFTER resolving access and discard it after the read.
Folder rows and channel summaries may share it, but may only narrow its scope.
"""
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import exists
from sqlalchemy.orm import Session

from core import models


@dataclass(frozen=True)
class SummaryScope:
    client_ids: frozenset[UUID]
    rows: tuple[Any, ...]

    @classmethod
    def load(cls, db: Session, client_ids):
        ids = frozenset(client_ids)
        if not ids:
            return cls(ids, ())
        active = exists().where(
            models.Campaign.integration_id == models.Integration.id,
            models.Campaign.is_active.is_(True),
        )
        rows = db.query(
            models.Integration.id,
            models.Integration.client_id,
            models.Integration.platform,
            models.Integration.selected_goals,
            models.Integration.primary_goal_id,
            models.Integration.lead_action_types,
            models.Integration.balance,
            models.Integration.currency,
            active.label("has_active_campaign"),
        ).filter(models.Integration.client_id.in_(ids)).all()
        return cls(ids, tuple(rows))

    def rows_for(self, client_ids):
        ids = frozenset(client_ids)
        if not ids.issubset(self.client_ids):
            raise ValueError("Summary scope cannot be expanded")
        return tuple(row for row in self.rows if row.client_id in ids)
