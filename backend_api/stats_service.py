from sqlalchemy.orm import Session
from sqlalchemy import func
from core import models
from datetime import datetime, timedelta
import uuid
import json
import os
from typing import List, Optional

class StatsService:
    @staticmethod
    def get_metrika_goal_integration_ids(
        db: Session,
        client_ids: List[uuid.UUID],
        platform: str = "all",
    ) -> List[uuid.UUID]:
        platform_key = (platform or "all").lower()
        if platform_key == "avito":
            platforms = [models.IntegrationPlatform.AVITO_ADS]
        elif platform_key == "yandex":
            platforms = [
                models.IntegrationPlatform.YANDEX_DIRECT,
                models.IntegrationPlatform.YANDEX_METRIKA,
            ]
        else:
            return []

        return [
            row[0]
            for row in db.query(models.Integration.id)
            .filter(
                models.Integration.client_id.in_(client_ids),
                models.Integration.platform.in_(platforms),
            )
            .all()
            if row[0]
        ]

    @staticmethod
    def get_selected_metrika_goal_ids(
        db: Session,
        client_ids: List[uuid.UUID],
        platform: str = "all",
    ) -> List[str]:
        platform_key = (platform or "all").lower()
        if platform_key == "avito":
            platforms = [models.IntegrationPlatform.AVITO_ADS]
        elif platform_key == "yandex":
            platforms = [models.IntegrationPlatform.YANDEX_DIRECT]
        else:
            platforms = [
                models.IntegrationPlatform.YANDEX_DIRECT,
                models.IntegrationPlatform.YANDEX_METRIKA,
                models.IntegrationPlatform.AVITO_ADS,
            ]

        goal_ids: List[str] = []
        for integration in db.query(models.Integration).filter(
            models.Integration.client_id.in_(client_ids),
            models.Integration.platform.in_(platforms),
        ).all():
            if integration.selected_goals:
                try:
                    parsed = json.loads(integration.selected_goals) if isinstance(integration.selected_goals, str) else integration.selected_goals
                    for goal_id in parsed or []:
                        goal_id = str(goal_id)
                        if goal_id and goal_id not in goal_ids:
                            goal_ids.append(goal_id)
                except Exception:
                    pass
            if integration.primary_goal_id:
                primary_goal = str(integration.primary_goal_id)
                if primary_goal and primary_goal not in goal_ids:
                    goal_ids.append(primary_goal)

        if not goal_ids and platform_key == "yandex":
            # Backward compatibility: older Yandex setups may store selected
            # goals on the companion Metrika integration.
            for integration in db.query(models.Integration).filter(
                models.Integration.client_id.in_(client_ids),
                models.Integration.platform == models.IntegrationPlatform.YANDEX_METRIKA,
            ).all():
                if integration.selected_goals:
                    try:
                        parsed = json.loads(integration.selected_goals) if isinstance(integration.selected_goals, str) else integration.selected_goals
                        for goal_id in parsed or []:
                            goal_id = str(goal_id)
                            if goal_id and goal_id not in goal_ids:
                                goal_ids.append(goal_id)
                    except Exception:
                        pass
                if integration.primary_goal_id:
                    primary_goal = str(integration.primary_goal_id)
                    if primary_goal and primary_goal not in goal_ids:
                        goal_ids.append(primary_goal)

        return goal_ids

    @staticmethod
    def get_effective_client_ids(db: Session, user_id: uuid.UUID, client_id: Optional[uuid.UUID] = None) -> List[uuid.UUID]:
        member = (
            db.query(models.TeamMember)
            .filter(
                models.TeamMember.user_id == user_id,
                models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
            )
            .first()
        )
        if member:
            # Member: own projects + shared team projects. Client: only shared.
            own_ids = []
            if member.role == models.TeamMemberRole.MEMBER:
                own_ids = [r[0] for r in db.query(models.Client.id).filter(models.Client.owner_id == user_id).all()]
            shared_ids = [
                r[0]
                for r in (
                    db.query(models.TeamMemberProject.project_id)
                    .join(models.Client, models.Client.id == models.TeamMemberProject.project_id)
                    .filter(models.TeamMemberProject.team_member_id == member.id)
                    .all()
                )
            ]
            all_ids = list(dict.fromkeys(own_ids + shared_ids))
            if client_id:
                return [client_id] if client_id in all_ids else []
            return all_ids

        if client_id:
            client = db.query(models.Client).filter_by(id=client_id, owner_id=user_id).first()
            if client:
                return [client_id]
            # Owner sees all projects of team members too.
            member_user_ids = [
                r[0]
                for r in (
                    db.query(models.TeamMember.user_id)
                    .filter(
                        models.TeamMember.account_id == user_id,
                        models.TeamMember.role == models.TeamMemberRole.MEMBER,
                        models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
                        models.TeamMember.user_id.isnot(None),
                    )
                    .all()
                )
            ]
            team_client = None
            if member_user_ids:
                team_client = db.query(models.Client).filter(models.Client.id == client_id, models.Client.owner_id.in_(member_user_ids)).first()
            return [client_id] if team_client else []
        own = [c.id for c in db.query(models.Client).filter_by(owner_id=user_id).all()]
        member_user_ids = [
            r[0]
            for r in (
                db.query(models.TeamMember.user_id)
                .filter(
                    models.TeamMember.account_id == user_id,
                    models.TeamMember.role == models.TeamMemberRole.MEMBER,
                    models.TeamMember.status == models.TeamMemberStatus.ACTIVE,
                    models.TeamMember.user_id.isnot(None),
                )
                .all()
            )
        ]
        team = []
        if member_user_ids:
            team = [c.id for c in db.query(models.Client).filter(models.Client.owner_id.in_(member_user_ids)).all()]
        return list(dict.fromkeys(own + team))

    @staticmethod
    def aggregate_summary(
        db: Session,
        client_ids: List[uuid.UUID],
        d_start: Optional[datetime.date],
        d_end: datetime.date,
        platform: str = "all",
        campaign_ids: Optional[List[uuid.UUID]] = None,
        vk_goal_action_ids: Optional[List[str]] = None
    ):
        if not client_ids:
            return {
                "expenses": 0,
                "impressions": 0,
                "clicks": 0,
                "leads": 0,
                "cpc": 0,
                "cpa": 0,
                "ctr": 0,
                "cr": 0,
                "balance": 0,
                "currency": "RUB",
                "leads_available": True,
                "cpa_available": True,
                "goals_syncing": False,
                "goals_sync_message": None,
                "trends": None
            }

        selected_platforms = [
            row[0]
            for row in db.query(models.Integration.platform)
            .filter(models.Integration.client_id.in_(client_ids))
            .distinct()
            .all()
        ]
        has_yandex_platform = any(
            p in [models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.YANDEX_METRIKA]
            for p in selected_platforms
        )
        has_vk_platform = models.IntegrationPlatform.VK_ADS in selected_platforms
        selected_campaign_platforms = []
        if campaign_ids:
            selected_campaign_integration_ids = [
                row[0]
                for row in db.query(models.Campaign.integration_id)
                .filter(models.Campaign.id.in_(campaign_ids))
                .distinct()
                .all()
                if row[0]
            ]
            if selected_campaign_integration_ids:
                selected_campaign_platforms = [
                    row[0]
                    for row in db.query(models.Integration.platform)
                    .filter(models.Integration.id.in_(selected_campaign_integration_ids))
                    .distinct()
                    .all()
                ]
        metrika_goal_platform = platform
        if platform == "all" and selected_campaign_platforms:
            if all(p == models.IntegrationPlatform.AVITO_ADS for p in selected_campaign_platforms):
                metrika_goal_platform = "avito"
            elif all(p == models.IntegrationPlatform.YANDEX_DIRECT for p in selected_campaign_platforms):
                metrika_goal_platform = "yandex"
        selected_goal_ids_for_summary = set(
            StatsService.get_selected_metrika_goal_ids(db, client_ids, metrika_goal_platform)
        )

        def get_data(start, end):
            y_q = db.query(
                func.sum(models.YandexStats.cost).label("total_cost"),
                func.sum(models.YandexStats.impressions).label("total_impressions"),
                func.sum(models.YandexStats.clicks).label("total_clicks"),
                func.sum(models.YandexStats.conversions).label("total_conversions")
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id.in_(client_ids)
            )

            # CRITICAL: Для VK Ads CPC — взвешенное среднее; CPA — все затраты / лиды (как в интерфейсе VK)
            v_q = db.query(
                func.sum(models.VKStats.cost).label("total_cost"),
                func.sum(models.VKStats.impressions).label("total_impressions"),
                func.sum(models.VKStats.clicks).label("total_clicks"),
                func.sum(models.VKStats.conversions).label("total_conversions"),
                # Взвешенное среднее CPC: sum(cpc * clicks) / sum(clicks)
                func.sum(models.VKStats.cpc * models.VKStats.clicks).label("weighted_cpc_sum")
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(client_ids)
            )
            a_q = db.query(
                func.sum(models.AvitoStats.cost).label("total_cost"),
                func.sum(models.AvitoStats.impressions).label("total_impressions"),
                func.sum(models.AvitoStats.clicks).label("total_clicks"),
                func.sum(models.AvitoStats.conversions).label("total_conversions"),
                func.sum(models.AvitoStats.cpc * models.AvitoStats.clicks).label("weighted_cpc_sum")
            ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
                models.AvitoStats.client_id.in_(client_ids)
            )

            # CRITICAL: Always filter by integration_id to prevent mixing data from different profiles
            # Even when campaigns are not selected, we should only show stats from campaigns
            # that belong to integrations of the selected client_id
            integration_ids = None
            
            if campaign_ids:
                y_q = y_q.filter(models.Campaign.id.in_(campaign_ids))
                v_q = v_q.filter(models.Campaign.id.in_(campaign_ids))
                a_q = a_q.filter(models.Campaign.id.in_(campaign_ids))

                # Get integration_ids for selected campaigns
                campaign_integrations = db.query(models.Campaign.integration_id).filter(
                    models.Campaign.id.in_(campaign_ids)
                ).distinct().all()
                integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
                
                if integration_ids:
                    y_q = y_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    v_q = v_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    a_q = a_q.filter(models.Campaign.integration_id.in_(integration_ids))
            else:
                # При "все кампании" считаем все кампании, где были данные в
                # выбранном периоде. Остановленные/архивные кампании не должны
                # исчезать из исторической статистики.
                if len(client_ids) == 1:
                    client_int = db.query(models.Integration.id).filter(
                        models.Integration.client_id.in_(client_ids)
                    ).distinct().all()
                    integration_ids = [ci[0] for ci in client_int if ci[0]]

            if vk_goal_action_ids:
                v_q = v_q.filter(models.Campaign.vk_goal_action_id.in_(vk_goal_action_ids))
                # Для VK при выборе целей — фильтр по интеграциям клиента
                if len(client_ids) == 1 and integration_ids:
                    y_q = y_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    v_q = v_q.filter(models.Campaign.integration_id.in_(integration_ids))
            
            # Print the actual query for one of them to see the SQL
            # print(f"DEBUG: Y_QUERY: {y_q}")

            # 3. Yandex Metrica Goals — Лиды = сумма по целям.
            # Фильтр по selected_goals: только цели, выбранные пользователем при интеграции.
            m_q = db.query(
                func.sum(models.MetrikaGoals.conversion_count).label("total_conversions")
            ).filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id != "all"
            )
            selected_goal_ids = set(selected_goal_ids_for_summary)
            if selected_goal_ids:
                m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
            elif platform == "avito":
                m_q = m_q.filter(models.MetrikaGoals.goal_id == "__no_avito_goal_selected__")
            
            # Для campaign drill-down фильтруем цели по интеграциям выбранных кампаний.
            # Для platform=avito/yandex без campaign_ids ограничиваемся интеграциями
            # соответствующей платформы, чтобы не смешивать одинаковые goal_id разных каналов.
            if campaign_ids and integration_ids:
                m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(integration_ids))
            else:
                goal_scope_ids = StatsService.get_metrika_goal_integration_ids(
                    db,
                    client_ids,
                    metrika_goal_platform,
                )
                if goal_scope_ids:
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
                elif metrika_goal_platform in ("avito", "yandex"):
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.is_(None))

            if start:
                y_q = y_q.filter(models.YandexStats.date >= start)
                v_q = v_q.filter(models.VKStats.date >= start)
                a_q = a_q.filter(models.AvitoStats.date >= start)
                m_q = m_q.filter(models.MetrikaGoals.date >= start)
            if end:
                y_q = y_q.filter(models.YandexStats.date <= end)
                v_q = v_q.filter(models.VKStats.date <= end)
                a_q = a_q.filter(models.AvitoStats.date <= end)
                m_q = m_q.filter(models.MetrikaGoals.date <= end)

            def get_yandex_scope_cost():
                if not campaign_ids:
                    return float((y_s.total_cost if y_s else 0) or 0)
                scope_q = db.query(
                    func.sum(models.YandexStats.cost)
                ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                    models.YandexStats.client_id.in_(client_ids)
                )
                if integration_ids:
                    scope_q = scope_q.filter(models.Campaign.integration_id.in_(integration_ids))
                if start:
                    scope_q = scope_q.filter(models.YandexStats.date >= start)
                if end:
                    scope_q = scope_q.filter(models.YandexStats.date <= end)
                return float((scope_q.scalar() or 0) or 0)

            def get_avito_scope_cost():
                if not campaign_ids:
                    return float((a_s.total_cost if a_s else 0) or 0)
                scope_q = db.query(
                    func.sum(models.AvitoStats.cost)
                ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
                    models.AvitoStats.client_id.in_(client_ids)
                )
                if integration_ids:
                    scope_q = scope_q.filter(models.Campaign.integration_id.in_(integration_ids))
                if start:
                    scope_q = scope_q.filter(models.AvitoStats.date >= start)
                if end:
                    scope_q = scope_q.filter(models.AvitoStats.date <= end)
                return float((scope_q.scalar() or 0) or 0)

            # CRITICAL: Log the date range and integration filter for debugging
            import logging
            debug_logger = logging.getLogger(__name__)
            debug_logger.info(f"🔍 StatsService.get_data - Date range: {start} to {end}")
            debug_logger.info(f"🔍 Integration IDs: {integration_ids}")
            debug_logger.info(f"🔍 Client IDs: {client_ids}")
            debug_logger.info(f"🔍 Campaign IDs: {campaign_ids}")
            
            # CRITICAL: Check what data actually exists in DB for this date range
            if os.getenv("ENABLE_STATS_DEBUG_SAMPLE", "false").lower() == "true" and platform in ["all", "yandex"]:
                sample_query = db.query(
                    models.YandexStats.date,
                    models.Campaign.name,
                    func.sum(models.YandexStats.impressions).label("imps"),
                    func.sum(models.YandexStats.clicks).label("clicks"),
                    func.sum(models.YandexStats.cost).label("cost")
                ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                    models.YandexStats.client_id.in_(client_ids),
                    models.YandexStats.date >= start,
                    models.YandexStats.date <= end
                )
                if integration_ids:
                    sample_query = sample_query.filter(models.Campaign.integration_id.in_(integration_ids))
                if campaign_ids:
                    sample_query = sample_query.filter(models.Campaign.id.in_(campaign_ids))
                sample_data = sample_query.group_by(models.YandexStats.date, models.Campaign.name).limit(10).all()
                debug_logger.info(f"🔍 Sample data in DB for date range {start} to {end}: {len(sample_data)} rows")
                for row in sample_data[:5]:
                    debug_logger.info(f"🔍   Date: {row.date}, Campaign: {row.name}, Impressions: {row.imps}, Clicks: {row.clicks}, Cost: {row.cost}")

            y_s = y_q.first() if platform in ["all", "yandex"] else None
            v_s = v_q.first() if platform in ["all", "vk"] else None
            a_s = a_q.first() if platform in ["all", "avito"] else None
            m_s = m_q.first() if platform in ["all", "yandex", "avito"] else None

            costs = float((y_s.total_cost if y_s else 0) or 0) + float((v_s.total_cost if v_s else 0) or 0) + float((a_s.total_cost if a_s else 0) or 0)
            imps = int((y_s.total_impressions if y_s else 0) or 0) + int((v_s.total_impressions if v_s else 0) or 0) + int((a_s.total_impressions if a_s else 0) or 0)
            clks = int((y_s.total_clicks if y_s else 0) or 0) + int((v_s.total_clicks if v_s else 0) or 0) + int((a_s.total_clicks if a_s else 0) or 0)
            
            # CRITICAL: Лиды и конверсии для Yandex — только из Метрики (MetrikaGoals).
            # Direct conversions не подставляем fallback-ом, иначе дашборд расходится
            # со страницей проектов и выбранными целями.
            metrica_convs = int((m_s.total_conversions if m_s else 0) or 0)
            vk_convs = int((v_s.total_conversions if v_s else 0) or 0)
            mixed_goal_types = platform == "all" and not campaign_ids and has_yandex_platform and has_vk_platform
            yandex_cost = float((y_s.total_cost if y_s else 0) or 0)
            avito_cost = float((a_s.total_cost if a_s else 0) or 0)
            yandex_scope_cost = get_yandex_scope_cost()
            avito_scope_cost = get_avito_scope_cost()
            avito_metrika_convs = (
                int(round(metrica_convs * (avito_cost / avito_scope_cost)))
                if campaign_ids and metrica_convs > 0 and avito_cost > 0 and avito_scope_cost > 0
                else metrica_convs
            )
            if campaign_ids:
                yandex_metrika_convs = (
                    int(round(metrica_convs * (yandex_cost / yandex_scope_cost)))
                    if metrica_convs > 0 and yandex_cost > 0 and yandex_scope_cost > 0
                    else 0
                )
            else:
                yandex_metrika_convs = metrica_convs
            
            if platform == "vk":
                convs = vk_convs
                leads_available = True
                cpa_available = True
            elif platform == "avito":
                convs = avito_metrika_convs
                leads_available = True
                cpa_available = True
            elif campaign_ids:
                # Yandex-лиды берём только из Метрики по selected_goals. Так как
                # MetrikaGoals пока не хранит campaign_id, для направления
                # распределяем лиды по доле расхода выбранных кампаний.
                selected_has_yandex = models.IntegrationPlatform.YANDEX_DIRECT in selected_campaign_platforms
                selected_has_avito = models.IntegrationPlatform.AVITO_ADS in selected_campaign_platforms
                convs = (
                    (yandex_metrika_convs if selected_has_yandex or not selected_campaign_platforms else 0)
                    + vk_convs
                    + (avito_metrika_convs if selected_has_avito else 0)
                )
                leads_available = True
                cpa_available = True
            elif platform == "yandex":
                convs = metrica_convs
                leads_available = True
                cpa_available = True
            elif mixed_goal_types:
                # Яндекс и VK используют разные источники/типы целевых действий.
                # Показы, клики и расход можно суммировать; лиды/CPL показываем
                # отдельно по каналам, без фейкового общего числа.
                convs = metrica_convs
                leads_available = False
                cpa_available = False
            elif platform == "all":
                convs = metrica_convs if has_yandex_platform else vk_convs
                leads_available = True
                cpa_available = True
            else:
                convs = metrica_convs
                leads_available = True
                cpa_available = True
            
            # CRITICAL: Для VK Ads CPC — взвешенное среднее; CPA — все затраты / лиды (как в VK)
            vk_clicks = int((v_s.total_clicks if v_s else 0) or 0)
            vk_conversions = int((v_s.total_conversions if v_s else 0) or 0)
            vk_cost = float((v_s.total_cost if v_s else 0) or 0)
            vk_weighted_cpc_sum = float((v_s.weighted_cpc_sum if v_s and v_s.weighted_cpc_sum else 0) or 0)
            avito_clicks = int((a_s.total_clicks if a_s else 0) or 0)
            avito_conversions = int((a_s.total_conversions if a_s else 0) or 0)
            avito_weighted_cpc_sum = float((a_s.weighted_cpc_sum if a_s and a_s.weighted_cpc_sum else 0) or 0)

            # Взвешенное среднее CPC для VK: sum(cpc * clicks) / sum(clicks)
            vk_avg_cpc = vk_weighted_cpc_sum / vk_clicks if vk_clicks > 0 else 0.0
            # CPA для VK: все затраты / количество лидов (совпадает с интерфейсом VK)
            vk_avg_cpa = vk_cost / vk_conversions if vk_conversions > 0 else 0.0
            avito_avg_cpc = avito_weighted_cpc_sum / avito_clicks if avito_clicks > 0 else 0.0
            avito_leads_for_cpa = avito_metrika_convs if platform in ["all", "avito"] else avito_conversions
            avito_avg_cpa = avito_cost / avito_leads_for_cpa if avito_leads_for_cpa > 0 else 0.0
            
            # CPA для Yandex: всегда из Метрики (selected_goals); по выбранным
            # кампаниям используем ту же пропорциональную оценку, что и для лидов.
            yandex_convs_for_cpa = yandex_metrika_convs
            # Для Yandex: CPC из Директа, CPA — из целевых лидов.
            yandex_clicks = int((y_s.total_clicks if y_s else 0) or 0)
            yandex_avg_cpc = yandex_cost / yandex_clicks if yandex_clicks > 0 else 0.0
            yandex_avg_cpa = yandex_cost / yandex_convs_for_cpa if yandex_convs_for_cpa > 0 else 0.0
            
            # Объединяем CPC и CPA для обеих платформ
            # Если есть данные от обеих платформ, используем взвешенное среднее
            total_clicks_for_cpc = clks
            total_conversions_for_cpa = convs
            
            if total_clicks_for_cpc > 0:
                weighted_sum = (
                    yandex_avg_cpc * yandex_clicks
                    + vk_avg_cpc * vk_clicks
                    + avito_avg_cpc * avito_clicks
                )
                avg_cpc = weighted_sum / total_clicks_for_cpc
            else:
                avg_cpc = 0.0

            total_platform_conversions_for_cpa = yandex_convs_for_cpa + vk_conversions + avito_leads_for_cpa

            if not cpa_available:
                avg_cpa = 0.0
            elif platform == "all":
                avg_cpa = costs / convs if convs > 0 else 0.0
            elif total_platform_conversions_for_cpa > 0:
                avg_cpa = (
                    yandex_avg_cpa * yandex_convs_for_cpa
                    + vk_avg_cpa * vk_conversions
                    + avito_avg_cpa * avito_leads_for_cpa
                ) / total_platform_conversions_for_cpa
            else:
                avg_cpa = 0.0
            
            return {
                "costs": costs, 
                "imps": imps, 
                "clks": clks, 
                "convs": convs,
                "avg_cpc": avg_cpc,  # Взвешенное среднее CPC
                "avg_cpa": avg_cpa,  # Взвешенное среднее CPA
                "leads_available": leads_available,
                "cpa_available": cpa_available,
            }

        # Current period data
        curr = get_data(d_start, d_end)
        goals_syncing = False
        if (
            selected_goal_ids_for_summary
            and platform in ["all", "yandex", "avito"]
            and not campaign_ids
            and d_start
            and d_end
        ):
            metrika_rows_count = db.query(func.count(models.MetrikaGoals.id)).filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id.in_(selected_goal_ids_for_summary),
                models.MetrikaGoals.date >= d_start,
                models.MetrikaGoals.date <= d_end,
            ).scalar() or 0
            goals_syncing = metrika_rows_count == 0
        
        # Previous period data for trends
        trends = None
        if d_start:
            delta = (d_end - d_start).days + 1
            prev_start = d_start - timedelta(days=delta)
            prev_end = d_start - timedelta(days=1)
            prev = get_data(prev_start, prev_end)
            
            def calc_trend(c, p):
                """
                Calculate percentage change between current (c) and previous (p) value.
                Если в прошлом периоде данных не было (p == 0 или None), считаем тренд 0%,
                чтобы избежать «фейковых» 100% при первом появлении данных.
                """
                if p is None or p == 0:
                    return 0.0
                return round(((float(c or 0) - float(p)) / float(p)) * 100, 1)

            trends = {
                "expenses": calc_trend(curr["costs"], prev["costs"]),
                "impressions": calc_trend(curr["imps"], prev["imps"]),
                "clicks": calc_trend(curr["clks"], prev["clks"]),
                "leads": calc_trend(curr["convs"], prev["convs"]),
                "cpc": calc_trend(
                    curr.get("avg_cpc", 0) if curr.get("avg_cpc", 0) > 0 else (curr["costs"]/curr["clks"] if curr["clks"] > 0 else 0),
                    prev.get("avg_cpc", 0) if prev.get("avg_cpc", 0) > 0 else (prev["costs"]/prev["clks"] if prev["clks"] > 0 else 0)
                ),
                "cpa": calc_trend(
                    curr.get("avg_cpa", 0) if curr.get("avg_cpa", 0) > 0 else (curr["costs"]/curr["convs"] if curr["convs"] > 0 else 0),
                    prev.get("avg_cpa", 0) if prev.get("avg_cpa", 0) > 0 else (prev["costs"]/prev["convs"] if prev["convs"] > 0 else 0)
                ),
                "ctr": calc_trend(curr["clks"]/curr["imps"] if curr["imps"] > 0 else 0,
                               prev["clks"]/prev["imps"] if prev["imps"] > 0 else 0),
                "cr": calc_trend(curr["convs"]/curr["clks"] if curr["clks"] > 0 else 0,
                               prev["convs"]/prev["clks"] if prev["clks"] > 0 else 0)
            }

        # CRITICAL: Используем CPC и CPA из get_data
        # VK: CPC — взвешенное среднее, CPA — затраты/лиды. Yandex: costs/clicks, costs/conversions
        cpc = curr.get("avg_cpc", 0) if curr.get("avg_cpc", 0) > 0 else (curr["costs"] / curr["clks"] if curr["clks"] > 0 else 0)
        cpa = curr.get("avg_cpa", 0) if curr.get("cpa_available", True) and curr.get("avg_cpa", 0) > 0 else 0
        ctr = (curr["clks"] / curr["imps"] * 100) if curr["imps"] > 0 else 0
        cr = (curr["convs"] / curr["clks"] * 100) if curr.get("leads_available", True) and curr["clks"] > 0 else 0

        # Агрегируем балансы из интеграций для выбранных клиентов
        # CRITICAL: Всегда фильтруем балансы по интеграциям активных кампаний
        # Это гарантирует, что баланс берется только из интеграции выбранного профиля
        # Даже когда выбраны "Все кампании", берем баланс только из интеграций с активными кампаниями
        
        # Сначала получаем integration_ids из активных кампаний
        active_campaigns_query = db.query(models.Campaign.integration_id).join(
            models.Integration
        ).filter(
            models.Integration.client_id.in_(client_ids),
            models.Campaign.is_active.is_(True)
        )
        
        # Если выбраны конкретные кампании, фильтруем по ним
        if campaign_ids:
            active_campaigns_query = active_campaigns_query.filter(models.Campaign.id.in_(campaign_ids))

        if platform == "yandex":
            active_campaigns_query = active_campaigns_query.filter(
                models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
            )
        elif platform == "vk":
            active_campaigns_query = active_campaigns_query.filter(
                models.Integration.platform == models.IntegrationPlatform.VK_ADS
            )
        elif platform == "avito":
            active_campaigns_query = active_campaigns_query.filter(
                models.Integration.platform == models.IntegrationPlatform.AVITO_ADS
            )
        elif platform == "all":
            active_campaigns_query = active_campaigns_query.filter(
                models.Integration.platform.in_([
                    models.IntegrationPlatform.YANDEX_DIRECT,
                    models.IntegrationPlatform.VK_ADS,
                    models.IntegrationPlatform.AVITO_ADS,
                ])
            )
        
        active_integration_ids = [ci[0] for ci in active_campaigns_query.distinct().all() if ci[0]]
        
        # CRITICAL: Фильтруем балансы только по интеграциям с активными кампаниями
        # Это гарантирует, что баланс берется только из интеграции выбранного профиля
        if not active_integration_ids:
            # Если нет активных кампаний, баланс недоступен
            import logging
            debug_logger = logging.getLogger(__name__)
            debug_logger.warning(f"⚠️ No active campaigns found. Balance will be None.")
            all_balances = []
            total_balance = None
            balance_currency = None
            # Пропускаем дальнейшую обработку балансов
            return {
                "expenses": round(curr["costs"], 2),
                "impressions": int(curr["imps"]),
                "clicks": int(curr["clks"]),
                "leads": int(curr["convs"]),
                "cpc": round(cpc, 2),
                "cpa": round(cpa, 2),
                "ctr": round(ctr, 2),
                "cr": round(cr, 2),
                "balance": None,
                "currency": None,
                "leads_available": bool(curr.get("leads_available", True)),
                "cpa_available": bool(curr.get("cpa_available", True)),
                "goals_syncing": goals_syncing,
                "goals_sync_message": "Данные целей ещё синхронизируются" if goals_syncing else None,
                "revenue": 0.0,
                "profit": -round(curr["costs"], 2),
                "roi": -100.0 if curr["costs"] > 0 else 0.0,
                "trends": trends
            }
        
        # CRITICAL: Запрашиваем балансы ТОЛЬКО из интеграций с активными кампаниями
        # Исключаем балансы равные None И 0.0
        balance_query = db.query(
            models.Integration.balance,
            models.Integration.currency
        ).filter(
            models.Integration.id.in_(active_integration_ids),
            models.Integration.balance.isnot(None),
            models.Integration.balance != 0.0  # CRITICAL: Исключаем балансы равные 0.0
        )
        
        all_balances = balance_query.all()
        
        # CRITICAL: Логируем найденные балансы для отладки
        import logging
        debug_logger = logging.getLogger(__name__)
        debug_logger.info(f"💰 Balance query: client_ids={client_ids}, campaign_ids={campaign_ids}, active_integration_ids={active_integration_ids}")
        debug_logger.info(f"💰 Found {len(all_balances)} integration(s) with non-zero balance")
        
        # Дополнительная проверка: если балансы найдены, но они все 0.0 - считаем их как отсутствующие
        if all_balances:
            # Фильтруем балансы - исключаем те, которые равны 0.0 (на случай если фильтр не сработал)
            non_zero_balances = [b for b in all_balances if b.balance is not None and float(b.balance) != 0.0]
            if not non_zero_balances:
                debug_logger.warning(f"⚠️ All balances are 0.0 or None. Treating as no balance available.")
                all_balances = []
            else:
                for b in non_zero_balances:
                    debug_logger.info(f"💰   Balance: {b.balance} {b.currency}")
        
        if all_balances:
            # Суммируем балансы, предпочитая RUB
            total_balance = 0.0
            balance_currency = "RUB"
            
            # Сначала пробуем найти валюту RUB
            rub_balances = [b for b in all_balances if b.currency == "RUB"]
            if rub_balances:
                total_balance = sum(float(b.balance) if b.balance is not None else 0.0 for b in rub_balances)
                balance_currency = "RUB"
            else:
                # Если RUB нет, суммируем все балансы и берем первую валюту
                currencies = set(b.currency or "RUB" for b in all_balances)
                if len(currencies) == 1:
                    # Все в одной валюте - суммируем все
                    balance_currency = list(currencies)[0]
                    total_balance = sum(float(b.balance) if b.balance is not None else 0.0 for b in all_balances)
                else:
                    # Разные валюты - берем первую найденную и суммируем только её
                    balance_currency = all_balances[0].currency or "RUB"
                    same_currency_balances = [b for b in all_balances if (b.currency or "RUB") == balance_currency]
                    total_balance = sum(float(b.balance) if b.balance is not None else 0.0 for b in same_currency_balances)
        else:
            # CRITICAL: Если балансов нет (все None), возвращаем None вместо 0.0
            # Это позволяет фронтенду скрыть баланс на дашборде
            total_balance = None
            balance_currency = None

        return {
            "expenses": round(curr["costs"], 2),
            "impressions": int(curr["imps"]),
            "clicks": int(curr["clks"]),
            "leads": int(curr["convs"]),
            "cpc": round(cpc, 2),
            "cpa": round(cpa, 2),
            "ctr": round(ctr, 2),
            "cr": round(cr, 2),
            "balance": round(total_balance, 2) if total_balance is not None else None,
            "currency": balance_currency,
            "leads_available": bool(curr.get("leads_available", True)),
            "cpa_available": bool(curr.get("cpa_available", True)),
            "goals_syncing": goals_syncing,
            "goals_sync_message": "Данные целей ещё синхронизируются" if goals_syncing else None,
            "revenue": 0.0,  # Placeholder for future financial integration
            "profit": -round(curr["costs"], 2),
            "roi": -100.0 if curr["costs"] > 0 else 0.0,
            "trends": trends
        }

    @staticmethod
    def get_campaign_stats(
        db: Session,
        client_ids: List[uuid.UUID],
        d_start: Optional[datetime.date],
        d_end: datetime.date,
        platform: str = "all",
        campaign_ids: Optional[List[uuid.UUID]] = None,
        vk_goal_action_ids: Optional[List[str]] = None
    ):
        if not client_ids:
            return []

        def calc_trend(c, p):
            if p is None or p == 0:
                return 0.0
            return round(((float(c or 0) - float(p)) / float(p)) * 100, 1)

        # Previous period: same length, immediately before current
        prev_start = None
        prev_end = None
        if d_start:
            delta = (d_end - d_start).days + 1
            prev_start = d_start - timedelta(days=delta)
            prev_end = d_start - timedelta(days=1)

        # При "все кампании" фильтруем по интеграциям проекта, но не по
        # Campaign.is_active: остановленные/архивные кампании должны оставаться
        # в исторической статистике выбранного периода.
        integration_ids_filter = None
        selected_campaign_platforms = []
        if campaign_ids:
            campaign_integrations = db.query(models.Campaign.integration_id).filter(
                models.Campaign.id.in_(campaign_ids)
            ).distinct().all()
            aid_list = [r[0] for r in campaign_integrations if r[0]]
            if aid_list:
                integration_ids_filter = aid_list
                selected_campaign_platforms = [
                    row[0]
                    for row in db.query(models.Integration.platform)
                    .filter(models.Integration.id.in_(aid_list))
                    .distinct()
                    .all()
                ]
        elif len(client_ids) == 1:
            project_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(client_ids)
            ).distinct().all()
            aid_list = [r[0] for r in project_integrations if r[0]]
            if aid_list:
                integration_ids_filter = aid_list

        def run_yandex_query(start, end):
            q = db.query(
                models.Campaign.id.label("campaign_id"),
                models.YandexStats.campaign_name,
                func.sum(models.YandexStats.impressions).label("impressions"),
                func.sum(models.YandexStats.clicks).label("clicks"),
                func.sum(models.YandexStats.cost).label("cost"),
                func.sum(models.YandexStats.conversions).label("conversions")
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                q = q.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                q = q.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if start:
                q = q.filter(models.YandexStats.date >= start)
            if end:
                q = q.filter(models.YandexStats.date <= end)
            return q.group_by(models.Campaign.id, models.YandexStats.campaign_name).all()

        def get_yandex_scope_cost(start, end):
            q = db.query(
                func.sum(models.YandexStats.cost)
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id.in_(client_ids)
            )
            if integration_ids_filter:
                q = q.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if start:
                q = q.filter(models.YandexStats.date >= start)
            if end:
                q = q.filter(models.YandexStats.date <= end)
            return float((q.scalar() or 0) or 0)

        def run_vk_query(start, end):
            q = db.query(
                models.Campaign.id.label("campaign_id"),
                models.Campaign.name.label("campaign_display_name"),
                models.Campaign.external_id.label("campaign_external_id"),
                models.VKStats.campaign_name,
                func.sum(models.VKStats.impressions).label("impressions"),
                func.sum(models.VKStats.clicks).label("clicks"),
                func.sum(models.VKStats.cost).label("cost"),
                func.sum(models.VKStats.conversions).label("conversions")
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                q = q.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                q = q.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if vk_goal_action_ids:
                q = q.filter(models.Campaign.vk_goal_action_id.in_(vk_goal_action_ids))
            if start:
                q = q.filter(models.VKStats.date >= start)
            if end:
                q = q.filter(models.VKStats.date <= end)
            return q.group_by(models.Campaign.id, models.Campaign.name, models.Campaign.external_id, models.VKStats.campaign_name).all()

        def run_avito_query(start, end):
            q = db.query(
                models.Campaign.id.label("campaign_id"),
                models.Campaign.name.label("campaign_display_name"),
                models.Campaign.external_id.label("campaign_external_id"),
                models.AvitoStats.campaign_name,
                func.sum(models.AvitoStats.impressions).label("impressions"),
                func.sum(models.AvitoStats.clicks).label("clicks"),
                func.sum(models.AvitoStats.cost).label("cost"),
                func.sum(models.AvitoStats.conversions).label("conversions")
            ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
                models.AvitoStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                q = q.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                q = q.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if start:
                q = q.filter(models.AvitoStats.date >= start)
            if end:
                q = q.filter(models.AvitoStats.date <= end)
            return q.group_by(models.Campaign.id, models.Campaign.name, models.Campaign.external_id, models.AvitoStats.campaign_name).all()

        def get_avito_scope_cost(start, end):
            scope_q = db.query(func.sum(models.AvitoStats.cost)).join(
                models.Campaign,
                models.AvitoStats.campaign_id == models.Campaign.id,
            ).filter(models.AvitoStats.client_id.in_(client_ids))
            scope_integration_ids = integration_ids_filter
            if not scope_integration_ids and campaign_ids:
                camp_int = db.query(models.Campaign.integration_id).filter(
                    models.Campaign.id.in_(campaign_ids)
                ).distinct().all()
                scope_integration_ids = [c[0] for c in camp_int if c[0]]
            if scope_integration_ids:
                scope_q = scope_q.filter(models.Campaign.integration_id.in_(scope_integration_ids))
            if start:
                scope_q = scope_q.filter(models.AvitoStats.date >= start)
            if end:
                scope_q = scope_q.filter(models.AvitoStats.date <= end)
            return float((scope_q.scalar() or 0) or 0)

        def get_metrika_convs(start, end, *, filter_by_campaign_integrations: bool = True):
            m_q = db.query(
                func.sum(models.MetrikaGoals.conversion_count).label("total")
            ).filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id != "all"
            )

            # Mirror the selected_goals filter from aggregate_summary so Metrika
            # conversions only count goals the user actually configured.
            metrika_goal_platform = platform
            if platform == "all" and selected_campaign_platforms:
                if all(p == models.IntegrationPlatform.AVITO_ADS for p in selected_campaign_platforms):
                    metrika_goal_platform = "avito"
                elif all(p == models.IntegrationPlatform.YANDEX_DIRECT for p in selected_campaign_platforms):
                    metrika_goal_platform = "yandex"
            selected_goal_ids = set(
                StatsService.get_selected_metrika_goal_ids(db, client_ids, metrika_goal_platform)
            )
            if selected_goal_ids:
                m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
            elif metrika_goal_platform == "avito":
                m_q = m_q.filter(models.MetrikaGoals.goal_id == "__no_avito_goal_selected__")

            if filter_by_campaign_integrations:
                m_int_ids = integration_ids_filter
                if not m_int_ids and campaign_ids:
                    camp_int = db.query(models.Campaign.integration_id).filter(
                        models.Campaign.id.in_(campaign_ids)
                    ).distinct().all()
                    m_int_ids = [c[0] for c in camp_int if c[0]]
                if not m_int_ids and len(client_ids) == 1:
                    client_int = db.query(models.Integration.id).filter(
                        models.Integration.client_id.in_(client_ids)
                    ).distinct().all()
                    m_int_ids = [c[0] for c in client_int if c[0]]
                if m_int_ids:
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(m_int_ids))
                else:
                    goal_scope_ids = StatsService.get_metrika_goal_integration_ids(
                        db,
                        client_ids,
                        metrika_goal_platform,
                    )
                    if goal_scope_ids:
                        m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
                    elif metrika_goal_platform in ("avito", "yandex"):
                        m_q = m_q.filter(models.MetrikaGoals.integration_id.is_(None))
            else:
                goal_scope_ids = StatsService.get_metrika_goal_integration_ids(
                    db,
                    client_ids,
                    metrika_goal_platform,
                )
                if goal_scope_ids:
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
                elif metrika_goal_platform in ("avito", "yandex"):
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.is_(None))
            if start:
                m_q = m_q.filter(models.MetrikaGoals.date >= start)
            if end:
                m_q = m_q.filter(models.MetrikaGoals.date <= end)
            return int((m_q.scalar() or 0) or 0)

        campaigns = []

        if platform in ["all", "yandex"]:
            y_results = run_yandex_query(d_start, d_end)
            total_metrika_convs = get_metrika_convs(d_start, d_end)
            total_yandex_cost = get_yandex_scope_cost(d_start, d_end)

            # Previous period Yandex data keyed by campaign_id
            prev_y_rows = {}
            prev_total_metrika_convs = 0
            prev_total_yandex_cost = 0
            if prev_start is not None:
                prev_y_list = run_yandex_query(prev_start, prev_end)
                prev_y_rows = {str(r.campaign_id): r for r in prev_y_list}
                prev_total_metrika_convs = get_metrika_convs(prev_start, prev_end)
                prev_total_yandex_cost = get_yandex_scope_cost(prev_start, prev_end)

            for r in y_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                imps = int(r.impressions or 0)
                # CRITICAL: Конверсии Yandex — только из Метрики (пропорционально).
                if total_metrika_convs > 0 and total_yandex_cost > 0:
                    convs = round(total_metrika_convs * (cost / total_yandex_cost))
                else:
                    convs = 0
                cpc = round(cost / clicks, 2) if clicks > 0 else 0
                cpa = round(cost / convs, 2) if convs > 0 else 0

                # Previous period values for this campaign
                cid = str(r.campaign_id)
                p = prev_y_rows.get(cid)
                if p:
                    prev_cost = float(p.cost or 0)
                    prev_clicks = int(p.clicks or 0)
                    prev_imps = int(p.impressions or 0)
                    if prev_total_metrika_convs > 0 and prev_total_yandex_cost > 0:
                        prev_convs = round(prev_total_metrika_convs * (prev_cost / prev_total_yandex_cost))
                    else:
                        prev_convs = 0
                    prev_cpc = prev_cost / prev_clicks if prev_clicks > 0 else 0
                    prev_cpa = prev_cost / prev_convs if prev_convs > 0 else 0
                else:
                    prev_cost = prev_clicks = prev_imps = prev_convs = prev_cpc = prev_cpa = 0

                campaigns.append({
                    "id": cid,
                    "name": f"[ЯД] {r.campaign_name}",
                    "impressions": imps,
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "conversions": convs,
                    "cpc": cpc,
                    "cpa": cpa,
                    "trend_cost": calc_trend(cost, prev_cost),
                    "trend_impressions": calc_trend(imps, prev_imps),
                    "trend_clicks": calc_trend(clicks, prev_clicks),
                    "trend_conversions": calc_trend(convs, prev_convs),
                    "trend_cpc": calc_trend(cpc, prev_cpc),
                    "trend_cpa": calc_trend(cpa, prev_cpa),
                })

        if platform in ["all", "vk"]:
            v_results = run_vk_query(d_start, d_end)

            # Previous period VK data keyed by campaign_id
            prev_v_rows = {}
            if prev_start is not None:
                prev_v_rows = {str(r.campaign_id): r for r in run_vk_query(prev_start, prev_end)}

            for r in v_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = int(r.conversions or 0)
                imps = int(r.impressions or 0)
                cpc = round(cost / clicks, 2) if clicks > 0 else 0
                cpa = round(cost / convs, 2) if convs > 0 else 0

                cid = str(r.campaign_id)
                p = prev_v_rows.get(cid)
                if p:
                    prev_cost = float(p.cost or 0)
                    prev_clicks = int(p.clicks or 0)
                    prev_imps = int(p.impressions or 0)
                    prev_convs = int(p.conversions or 0)
                    prev_cpc = prev_cost / prev_clicks if prev_clicks > 0 else 0
                    prev_cpa = prev_cost / prev_convs if prev_convs > 0 else 0
                else:
                    prev_cost = prev_clicks = prev_imps = prev_convs = prev_cpc = prev_cpa = 0

                # Название: Campaign.name (из API); если "Campaign {id}" — показываем "Кампания (ID: X)"
                raw = (r.campaign_display_name or r.campaign_name or "").strip()
                ext_id = getattr(r, "campaign_external_id", None) or ""
                if raw and not (raw.startswith("Campaign ") and raw.replace("Campaign ", "").strip().isdigit()):
                    disp_name = raw
                elif ext_id:
                    disp_name = f"Кампания (ID: {ext_id})"
                else:
                    disp_name = raw or "Без названия"
                campaigns.append({
                    "id": cid,
                    "name": f"[VK] {disp_name}",
                    "impressions": imps,
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "conversions": convs,
                    "cpc": cpc,
                    "cpa": cpa,
                    "trend_cost": calc_trend(cost, prev_cost),
                    "trend_impressions": calc_trend(imps, prev_imps),
                    "trend_clicks": calc_trend(clicks, prev_clicks),
                    "trend_conversions": calc_trend(convs, prev_convs),
                    "trend_cpc": calc_trend(cpc, prev_cpc),
                    "trend_cpa": calc_trend(cpa, prev_cpa),
                })

        if platform in ["all", "avito"]:
            av_results = run_avito_query(d_start, d_end)
            total_avito_metrika_convs = get_metrika_convs(
                d_start,
                d_end,
                filter_by_campaign_integrations=False,
            )
            total_avito_cost = get_avito_scope_cost(d_start, d_end)
            prev_av_rows = {}
            prev_total_avito_metrika_convs = 0
            prev_total_avito_cost = 0
            if prev_start is not None:
                prev_av_rows = {str(r.campaign_id): r for r in run_avito_query(prev_start, prev_end)}
                prev_total_avito_metrika_convs = get_metrika_convs(
                    prev_start,
                    prev_end,
                    filter_by_campaign_integrations=False,
                )
                prev_total_avito_cost = get_avito_scope_cost(prev_start, prev_end)
            for r in av_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = (
                    round(total_avito_metrika_convs * (cost / total_avito_cost))
                    if total_avito_metrika_convs > 0 and total_avito_cost > 0
                    else int(r.conversions or 0)
                )
                imps = int(r.impressions or 0)
                cpc = round(cost / clicks, 2) if clicks > 0 else 0
                cpa = round(cost / convs, 2) if convs > 0 else 0
                cid = str(r.campaign_id)
                p = prev_av_rows.get(cid)
                if p:
                    prev_cost = float(p.cost or 0)
                    prev_clicks = int(p.clicks or 0)
                    prev_imps = int(p.impressions or 0)
                    prev_convs = (
                        round(prev_total_avito_metrika_convs * (prev_cost / prev_total_avito_cost))
                        if prev_total_avito_metrika_convs > 0 and prev_total_avito_cost > 0
                        else int(p.conversions or 0)
                    )
                    prev_cpc = prev_cost / prev_clicks if prev_clicks > 0 else 0
                    prev_cpa = prev_cost / prev_convs if prev_convs > 0 else 0
                else:
                    prev_cost = prev_clicks = prev_imps = prev_convs = prev_cpc = prev_cpa = 0
                raw = (r.campaign_display_name or r.campaign_name or "").strip()
                ext_id = getattr(r, "campaign_external_id", None) or ""
                if raw and not (raw.startswith("Campaign ") and raw.replace("Campaign ", "").strip().isdigit()):
                    disp_name = raw
                elif ext_id:
                    disp_name = f"Кампания (ID: {ext_id})"
                else:
                    disp_name = raw or "Без названия"
                campaigns.append({
                    "id": cid,
                    "name": f"[Avito] {disp_name}",
                    "impressions": imps,
                    "clicks": clicks,
                    "cost": round(cost, 2),
                    "conversions": convs,
                    "cpc": cpc,
                    "cpa": cpa,
                    "trend_cost": calc_trend(cost, prev_cost),
                    "trend_impressions": calc_trend(imps, prev_imps),
                    "trend_clicks": calc_trend(clicks, prev_clicks),
                    "trend_conversions": calc_trend(convs, prev_convs),
                    "trend_cpc": calc_trend(cpc, prev_cpc),
                    "trend_cpa": calc_trend(cpa, prev_cpa),
                })

        # Сортировка: сначала по лидам (заявкам) desc, затем по расходу desc
        campaigns.sort(key=lambda x: (x["conversions"], x["cost"]), reverse=True)
        return campaigns

    @staticmethod
    def get_activity_by_weekday(
        db: Session,
        client_ids: List[uuid.UUID],
        d_start: Optional[datetime.date],
        d_end: datetime.date,
        platform: str = "all",
        campaign_ids: Optional[List[uuid.UUID]] = None,
        vk_goal_action_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Агрегирует клики и лиды (конверсии) по дням недели отдельно.
        PostgreSQL EXTRACT(DOW FROM date): 0=Sunday, 1=Monday, ..., 6=Saturday.
        Возвращает: {"clicks": {"0": N, ...}, "leads": {"0": N, ...}}
        """
        empty = {str(i): 0 for i in range(7)}
        if not client_ids:
            return {"clicks": dict(empty), "leads": dict(empty)}

        integration_ids_filter = None
        if not campaign_ids and len(client_ids) == 1:
            project_integrations = db.query(models.Integration.id).filter(
                models.Integration.client_id.in_(client_ids)
            ).distinct().all()
            aid_list = [r[0] for r in project_integrations if r[0]]
            if aid_list:
                integration_ids_filter = aid_list

        clicks_result = {str(i): 0 for i in range(7)}
        leads_result = {str(i): 0 for i in range(7)}

        integration_ids_for_metrika = None
        campaign_platforms = []
        if campaign_ids:
            campaign_integrations = db.query(models.Campaign.integration_id).filter(
                models.Campaign.id.in_(campaign_ids)
            ).distinct().all()
            integration_ids_for_metrika = [ci[0] for ci in campaign_integrations if ci[0]]
            if integration_ids_for_metrika:
                campaign_platforms = [
                    row[0]
                    for row in db.query(models.Integration.platform)
                    .filter(models.Integration.id.in_(integration_ids_for_metrika))
                    .distinct()
                    .all()
                ]

        selected_campaigns_are_avito = bool(campaign_platforms) and all(
            p == models.IntegrationPlatform.AVITO_ADS for p in campaign_platforms
        )
        selected_campaigns_are_yandex = bool(campaign_platforms) and all(
            p == models.IntegrationPlatform.YANDEX_DIRECT for p in campaign_platforms
        )
        metrika_goal_platform = platform
        if platform == "all":
            if selected_campaigns_are_avito:
                metrika_goal_platform = "avito"
            elif selected_campaigns_are_yandex:
                metrika_goal_platform = "yandex"

        # selected_goal_ids для лидов Метрики (как в aggregate_summary)
        selected_goal_ids = set(
            StatsService.get_selected_metrika_goal_ids(db, client_ids, metrika_goal_platform)
        )

        if platform in ["all", "yandex"]:
            from sqlalchemy import extract
            # Клики — из YandexStats
            y_rows = db.query(
                extract('dow', models.YandexStats.date).label('dow'),
                func.sum(models.YandexStats.clicks).label('clicks')
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                y_rows = y_rows.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                y_rows = y_rows.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if d_start:
                y_rows = y_rows.filter(models.YandexStats.date >= d_start)
            if d_end:
                y_rows = y_rows.filter(models.YandexStats.date <= d_end)
            y_rows = y_rows.group_by(extract('dow', models.YandexStats.date)).all()
            for r in y_rows:
                dow = int(r.dow) if r.dow is not None else 0
                clicks_result[str(dow)] = clicks_result.get(str(dow), 0) + int(r.clicks or 0)

            if not selected_campaigns_are_avito:
                # Лиды Yandex — из MetrikaGoals (selected_goals), как в сводке.
                m_q = db.query(
                    extract('dow', models.MetrikaGoals.date).label('dow'),
                    func.sum(models.MetrikaGoals.conversion_count).label('leads')
                ).filter(
                    models.MetrikaGoals.client_id.in_(client_ids),
                    models.MetrikaGoals.goal_id != "all"
                )
                if selected_goal_ids:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
                if campaign_ids and integration_ids_for_metrika:
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(integration_ids_for_metrika))
                if d_start:
                    m_q = m_q.filter(models.MetrikaGoals.date >= d_start)
                if d_end:
                    m_q = m_q.filter(models.MetrikaGoals.date <= d_end)
                m_rows = m_q.group_by(extract('dow', models.MetrikaGoals.date)).all()
                for r in m_rows:
                    dow = int(r.dow) if r.dow is not None else 0
                    leads_result[str(dow)] = leads_result.get(str(dow), 0) + int(r.leads or 0)
                # НЕ используем fallback на YandexStats.conversions — они другие (Direct считает не по Metrika целям).
                # Лиды в диаграмме = ТЕ ЖЕ, что в сводке (MetrikaGoals). Если Metrika пусто — остаётся 0.

        if platform in ["all", "vk"]:
            from sqlalchemy import extract
            v_rows = db.query(
                extract('dow', models.VKStats.date).label('dow'),
                func.sum(models.VKStats.clicks).label('clicks'),
                func.sum(models.VKStats.conversions).label('leads')
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                v_rows = v_rows.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                v_rows = v_rows.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if vk_goal_action_ids:
                v_rows = v_rows.filter(models.Campaign.vk_goal_action_id.in_(vk_goal_action_ids))
            if d_start:
                v_rows = v_rows.filter(models.VKStats.date >= d_start)
            if d_end:
                v_rows = v_rows.filter(models.VKStats.date <= d_end)
            v_rows = v_rows.group_by(extract('dow', models.VKStats.date)).all()
            for r in v_rows:
                dow = int(r.dow) if r.dow is not None else 0
                clicks_result[str(dow)] = clicks_result.get(str(dow), 0) + int(r.clicks or 0)
                leads_result[str(dow)] = leads_result.get(str(dow), 0) + int(r.leads or 0)

        if platform in ["all", "avito"]:
            from sqlalchemy import extract
            av_rows = db.query(
                extract('dow', models.AvitoStats.date).label('dow'),
                func.sum(models.AvitoStats.clicks).label('clicks'),
                func.sum(models.AvitoStats.conversions).label('leads')
            ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
                models.AvitoStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                av_rows = av_rows.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                av_rows = av_rows.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if d_start:
                av_rows = av_rows.filter(models.AvitoStats.date >= d_start)
            if d_end:
                av_rows = av_rows.filter(models.AvitoStats.date <= d_end)
            av_rows = av_rows.group_by(extract('dow', models.AvitoStats.date)).all()
            for r in av_rows:
                dow = int(r.dow) if r.dow is not None else 0
                clicks_result[str(dow)] = clicks_result.get(str(dow), 0) + int(r.clicks or 0)
                leads_result[str(dow)] = leads_result.get(str(dow), 0) + int(r.leads or 0)

            if platform == "avito" or selected_campaigns_are_avito:
                m_q = db.query(
                    extract('dow', models.MetrikaGoals.date).label('dow'),
                    func.sum(models.MetrikaGoals.conversion_count).label('leads')
                ).filter(
                    models.MetrikaGoals.client_id.in_(client_ids),
                    models.MetrikaGoals.goal_id != "all"
                )
                if selected_goal_ids:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(selected_goal_ids))
                elif metrika_goal_platform == "avito":
                    m_q = m_q.filter(models.MetrikaGoals.goal_id == "__no_avito_goal_selected__")
                if campaign_ids and integration_ids_for_metrika:
                    m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(integration_ids_for_metrika))
                else:
                    goal_scope_ids = StatsService.get_metrika_goal_integration_ids(
                        db,
                        client_ids,
                        metrika_goal_platform,
                    )
                    if goal_scope_ids:
                        m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(goal_scope_ids))
                    elif metrika_goal_platform in ("avito", "yandex"):
                        m_q = m_q.filter(models.MetrikaGoals.integration_id.is_(None))
                if d_start:
                    m_q = m_q.filter(models.MetrikaGoals.date >= d_start)
                if d_end:
                    m_q = m_q.filter(models.MetrikaGoals.date <= d_end)
                for r in m_q.group_by(extract('dow', models.MetrikaGoals.date)).all():
                    dow = int(r.dow) if r.dow is not None else 0
                    leads_result[str(dow)] = int(r.leads or 0)

        return {"clicks": clicks_result, "leads": leads_result}
