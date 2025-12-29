from sqlalchemy.orm import Session
from sqlalchemy import func
from core import models
from datetime import datetime
import uuid
from typing import List, Optional

class StatsService:
    @staticmethod
    def get_effective_client_ids(db: Session, user_id: uuid.UUID, client_id: Optional[uuid.UUID] = None) -> List[uuid.UUID]:
        if client_id:
            client = db.query(models.Client).filter_by(id=client_id, owner_id=user_id).first()
            return [client_id] if client else []
        return [c.id for c in db.query(models.Client).filter_by(owner_id=user_id).all()]

    @staticmethod
    def aggregate_summary(db: Session, client_ids: List[uuid.UUID], d_start: Optional[datetime.date], d_end: datetime.date, platform: str = "all"):
        if not client_ids:
            return {"expenses": 0, "impressions": 0, "clicks": 0, "leads": 0, "cpc": 0, "cpa": 0}

        yandex_query = db.query(
            func.sum(models.YandexStats.cost).label("total_cost"),
            func.sum(models.YandexStats.impressions).label("total_impressions"),
            func.sum(models.YandexStats.clicks).label("total_clicks"),
            func.sum(models.YandexStats.conversions).label("total_conversions")
        ).filter(models.YandexStats.client_id.in_(client_ids))

        vk_query = db.query(
            func.sum(models.VKStats.cost).label("total_cost"),
            func.sum(models.VKStats.impressions).label("total_impressions"),
            func.sum(models.VKStats.clicks).label("total_clicks"),
            func.sum(models.VKStats.conversions).label("total_conversions")
        ).filter(models.VKStats.client_id.in_(client_ids))

        if d_start:
            yandex_query = yandex_query.filter(models.YandexStats.date >= d_start)
            vk_query = vk_query.filter(models.VKStats.date >= d_start)
        if d_end:
            yandex_query = yandex_query.filter(models.YandexStats.date <= d_end)
            vk_query = vk_query.filter(models.VKStats.date <= d_end)

        y_summary = yandex_query.first() if platform in ["all", "yandex"] else None
        v_summary = vk_query.first() if platform in ["all", "vk"] else None

        total_costs = float((y_summary.total_cost if y_summary else 0) or 0) + \
                      float((v_summary.total_cost if v_summary else 0) or 0)
        total_impressions = int((y_summary.total_impressions if y_summary else 0) or 0) + \
                            int((v_summary.total_impressions if v_summary else 0) or 0)
        total_clicks = int((y_summary.total_clicks if y_summary else 0) or 0) + \
                       int((v_summary.total_clicks if v_summary else 0) or 0)
        total_conversions = int((y_summary.total_conversions if y_summary else 0) or 0) + \
                            int((v_summary.total_conversions if v_summary else 0) or 0)

        cpc = total_costs / total_clicks if total_clicks > 0 else 0
        cpa = total_costs / total_conversions if total_conversions > 0 else 0

        return {
            "expenses": round(total_costs, 2),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "leads": total_conversions,
            "cpc": round(cpc, 2),
            "cpa": round(cpa, 2)
        }

    @staticmethod
    def get_campaign_stats(db: Session, client_ids: List[uuid.UUID], d_start: Optional[datetime.date], d_end: datetime.date, platform: str = "all"):
        if not client_ids:
            return []

        campaigns = []

        if platform in ["all", "yandex"]:
            y_query = db.query(
                models.YandexStats.campaign_name,
                func.sum(models.YandexStats.impressions).label("impressions"),
                func.sum(models.YandexStats.clicks).label("clicks"),
                func.sum(models.YandexStats.cost).label("cost"),
                func.sum(models.YandexStats.conversions).label("conversions")
            ).filter(models.YandexStats.client_id.in_(client_ids))

            if d_start:
                y_query = y_query.filter(models.YandexStats.date >= d_start)
            if d_end:
                y_query = y_query.filter(models.YandexStats.date <= d_end)

            y_results = y_query.group_by(models.YandexStats.campaign_name).all()
            for r in y_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = int(r.conversions or 0)
                campaigns.append({
                    "name": f"[ЯД] {r.campaign_name}",
                    "impressions": int(r.impressions or 0),
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "conversions": convs,
                    "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
                    "cpa": round(cost / convs, 2) if convs > 0 else 0
                })

        if platform in ["all", "vk"]:
            v_query = db.query(
                models.VKStats.campaign_name,
                func.sum(models.VKStats.impressions).label("impressions"),
                func.sum(models.VKStats.clicks).label("clicks"),
                func.sum(models.VKStats.cost).label("cost"),
                func.sum(models.VKStats.conversions).label("conversions")
            ).filter(models.VKStats.client_id.in_(client_ids))

            if d_start:
                v_query = v_query.filter(models.VKStats.date >= d_start)
            if d_end:
                v_query = v_query.filter(models.VKStats.date <= d_end)

            v_results = v_query.group_by(models.VKStats.campaign_name).all()
            for r in v_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = int(r.conversions or 0)
                campaigns.append({
                    "name": f"[VK] {r.campaign_name}",
                    "impressions": int(r.impressions or 0),
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "conversions": convs,
                    "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
                    "cpa": round(cost / convs, 2) if convs > 0 else 0
                })

        campaigns.sort(key=lambda x: x["cost"], reverse=True)
        return campaigns
