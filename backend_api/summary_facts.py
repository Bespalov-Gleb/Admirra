"""Request-local, bounded SQL batches for whole-project summary cards.

Only raw sums are batched; StatsService retains the canonical CPL/trend policy.
No cross-request cache, credentials, provider calls, or settings TTL. Construct
after access resolution, discard before any write. Campaign drill-down is not
supported and must keep its exact attribution path.
"""
from collections import OrderedDict
from types import SimpleNamespace

from sqlalchemy import func

from core import models


class SummaryFacts:
    PAGE_SIZE = 64
    MAX_GOAL_GROUPS = 25000

    def __init__(self, scope):
        self.scope = scope
        ids = sorted(scope.client_ids, key=str)
        self.pages = [ids[i:i + self.PAGE_SIZE] for i in range(0, len(ids), self.PAGE_SIZE)]
        self.page_for = {cid: index for index, page in enumerate(self.pages) for cid in page}
        self.cache = OrderedDict()

    def read(self, db, client_ids, start, end):
        if not set(client_ids).issubset(self.scope.client_ids):
            raise ValueError("Summary facts scope cannot be expanded")
        if len(client_ids) != 1:
            return None  # Folder totals keep the existing cross-project policy.
        cid = client_ids[0]
        key = (self.page_for[cid], start, end)
        if key not in self.cache:
            self.cache[key] = self._load(db, self.pages[key[0]], start, end)
            if len(self.cache) > 4:  # Bounded even with thousands of projects.
                self.cache.popitem(last=False)
        self.cache.move_to_end(key)
        page = self.cache[key]
        return page.get(cid) if page is not None else None

    def _load(self, db, ids, start, end):
        from backend_api.stats_service import StatsService
        result = {cid: {"goals": []} for cid in ids}

        def window(query, model):
            query = query.filter(model.client_id.in_(ids))
            if start:
                query = query.filter(model.date >= start)
            if end:
                query = query.filter(model.date <= end)
            return query

        for name, model in (("y", models.YandexStats), ("v", models.VKStats), ("a", models.AvitoStats)):
            fields = [func.sum(model.cost).label("total_cost"),
                      func.sum(model.impressions).label("total_impressions"),
                      func.sum(model.clicks).label("total_clicks"),
                      func.sum(model.conversions).label("total_conversions")]
            if name != "y":
                fields.append(func.sum(model.cpc * model.clicks).label("weighted_cpc_sum"))
            query = db.query(model.client_id, *fields).join(models.Campaign, model.campaign_id == models.Campaign.id)
            for row in window(query, model).group_by(model.client_id).all():
                result[row.client_id][name] = row

        model = models.VKStats
        query = db.query(model.client_id, func.sum(model.cost).label("total_cost"),
                         func.sum(model.conversions).label("total_conversions")).join(
            models.Campaign, model.campaign_id == models.Campaign.id)
        lead_scope = StatsService.get_vk_lead_action_scope(db, ids, integration_scope=self.scope)
        query = StatsService.apply_vk_lead_action_scope(query, db, ids, scope=lead_scope)
        for row in window(query, model).group_by(model.client_id).all():
            result[row.client_id]["vl"] = row

        model = models.MetrikaGoals
        query = db.query(model.client_id, model.integration_id, model.goal_id,
                         func.sum(model.conversion_count).label("total_conversions"))
        rows = window(query, model).group_by(model.client_id, model.integration_id, model.goal_id).limit(
            self.MAX_GOAL_GROUPS + 1).all()
        if len(rows) > self.MAX_GOAL_GROUPS:
            return None  # Fall back to exact SQL, never return truncated facts.
        for row in rows:
            result[row.client_id]["goals"].append(row)
        return result

    @staticmethod
    def metrika(facts, selected_goals, integration_ids, platform):
        total = 0
        for row in facts["goals"]:
            if row.goal_id is None or row.goal_id == "all":
                continue
            if selected_goals and row.goal_id not in selected_goals:
                continue
            if not selected_goals and platform == "avito":
                continue
            if integration_ids and row.integration_id not in integration_ids:
                continue
            if not integration_ids and platform in ("yandex", "avito") and row.integration_id is not None:
                continue
            total += row.total_conversions or 0
        return SimpleNamespace(total_conversions=total)

    @staticmethod
    def goals_present(facts, selected_goals):
        # Match the existing EXISTS exactly, including zero-valued rows.
        return any(row.goal_id in selected_goals for row in facts["goals"])
