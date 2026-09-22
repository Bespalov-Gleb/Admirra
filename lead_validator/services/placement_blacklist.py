"""Compatibility facade: global Redis placement decisions are no longer trusted.

Generate decisions with the durable lead.blacklist planner, not process memory.
Legacy keys cannot be safely assigned to a project and are deliberately ignored.
"""
from lead_validator.services import scoped_placements


class PlacementBlacklist:
    async def is_blacklisted(self, source, campaign, content, *, db, owner_id, project_id):
        return scoped_placements.is_blacklisted(db, owner_id, project_id, source, campaign, content)

    async def get_blacklist(self, *, db, owner_id):
        return scoped_placements.get_blacklist(db, owner_id)

    async def update_blacklist(self):
        raise RuntimeError('Global placement updates are unsafe; run the scoped durable lead.blacklist planner')


placement_blacklist = PlacementBlacklist()
