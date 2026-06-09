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
                "trends": None
            }

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
                print(f"DEBUG: StatsService.get_data - FILTERING by {len(campaign_ids)} campaigns: {campaign_ids}")
                y_q = y_q.filter(models.Campaign.id.in_(campaign_ids))
                v_q = v_q.filter(models.Campaign.id.in_(campaign_ids))
                a_q = a_q.filter(models.Campaign.id.in_(campaign_ids))
                
                # Get integration_ids for selected campaigns
                campaign_integrations = db.query(models.Campaign.integration_id).filter(
                    models.Campaign.id.in_(campaign_ids)
                ).distinct().all()
                integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
                
                if integration_ids:
                    print(f"DEBUG: StatsService.get_data - FILTERING by {len(integration_ids)} integrations from selected campaigns: {integration_ids}")
                    y_q = y_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    v_q = v_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    a_q = a_q.filter(models.Campaign.integration_id.in_(integration_ids))
            else:
                # When "all campaigns" option is selected on the dashboard,
                # we должны учитывать только кампании, которые пользователь включил в проект (is_active = True).
                y_q = y_q.filter(models.Campaign.is_active.is_(True))
                v_q = v_q.filter(models.Campaign.is_active.is_(True))
                a_q = a_q.filter(models.Campaign.is_active.is_(True))

                # integration_ids только для MetrikaGoals (m_q), НЕ для y_q/v_q — иначе ломается получение данных
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
                    a_q = a_q.filter(models.Campaign.integration_id.in_(integration_ids))
            
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
            selected_goal_ids = set()
            for i in db.query(models.Integration).filter(
                models.Integration.client_id.in_(client_ids),
                models.Integration.platform.in_([
                    models.IntegrationPlatform.YANDEX_DIRECT,
                    models.IntegrationPlatform.YANDEX_METRIKA,
                ]),
            ).all():
                if i.selected_goals:
                    try:
                        sg = json.loads(i.selected_goals) if isinstance(i.selected_goals, str) else i.selected_goals
                        selected_goal_ids.update(str(g) for g in (sg or []))
                    except Exception:
                        pass
                if i.primary_goal_id:
                    selected_goal_ids.add(str(i.primary_goal_id))
            if selected_goal_ids:
                synced_goal_ids = {
                    row[0]
                    for row in db.query(models.MetrikaGoals.goal_id)
                    .filter(
                        models.MetrikaGoals.client_id.in_(client_ids),
                        models.MetrikaGoals.goal_id != "all",
                    )
                    .distinct()
                    .all()
                }
                applicable = selected_goal_ids & synced_goal_ids
                if applicable:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(applicable))
                elif synced_goal_ids:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(synced_goal_ids))
            
            # Filter MetrikaGoals by integration_id только при выборе конкретных кампаний.
            # При "все кампании" — НЕ фильтруем m_q, чтобы получать все MetrikaGoals клиента.
            if campaign_ids and integration_ids:
                m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(integration_ids))

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
            
            # CRITICAL: Лиды и конверсии для Yandex — из Метрики (MetrikaGoals).
            # Fallback на Direct если Metrika ещё не синхронизирована (пусто 0).
            metrica_convs = int((m_s.total_conversions if m_s else 0) or 0)
            yandex_convs = int((y_s.total_conversions if y_s else 0) or 0)
            vk_convs = int((v_s.total_conversions if v_s else 0) or 0)
            if platform == "vk":
                convs = vk_convs
            elif platform == "avito":
                convs = metrica_convs
            elif platform in ["all", "yandex"]:
                convs = (metrica_convs if metrica_convs > 0 else yandex_convs) + vk_convs
            else:
                convs = (metrica_convs if metrica_convs > 0 else yandex_convs) + vk_convs 
            
            # CRITICAL: Для VK Ads CPC — взвешенное среднее; CPA — все затраты / лиды (как в VK)
            vk_clicks = int((v_s.total_clicks if v_s else 0) or 0)
            vk_conversions = int((v_s.total_conversions if v_s else 0) or 0)
            vk_cost = float((v_s.total_cost if v_s else 0) or 0)
            vk_weighted_cpc_sum = float((v_s.weighted_cpc_sum if v_s and v_s.weighted_cpc_sum else 0) or 0)
            avito_clicks = int((a_s.total_clicks if a_s else 0) or 0)
            avito_conversions = int((a_s.total_conversions if a_s else 0) or 0)
            avito_cost = float((a_s.total_cost if a_s else 0) or 0)
            avito_weighted_cpc_sum = float((a_s.weighted_cpc_sum if a_s and a_s.weighted_cpc_sum else 0) or 0)
            
            # Взвешенное среднее CPC для VK: sum(cpc * clicks) / sum(clicks)
            vk_avg_cpc = vk_weighted_cpc_sum / vk_clicks if vk_clicks > 0 else 0.0
            # CPA для VK: все затраты / количество лидов (совпадает с интерфейсом VK)
            vk_avg_cpa = vk_cost / vk_conversions if vk_conversions > 0 else 0.0
            avito_avg_cpc = avito_weighted_cpc_sum / avito_clicks if avito_clicks > 0 else 0.0
            avito_leads_for_cpa = metrica_convs if platform in ["all", "avito"] else avito_conversions
            avito_avg_cpa = avito_cost / avito_leads_for_cpa if avito_leads_for_cpa > 0 else 0.0
            
            # CPA для Yandex: Метрика приоритетна; fallback на Direct если Metrika пусто
            yandex_convs_for_cpa = metrica_convs if metrica_convs > 0 else yandex_convs
            # Для Yandex: CPC из Директа, CPA — из Метрики (fallback Direct)
            yandex_clicks = int((y_s.total_clicks if y_s else 0) or 0)
            yandex_cost = float((y_s.total_cost if y_s else 0) or 0)
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
            
            if total_platform_conversions_for_cpa > 0:
                avg_cpa = (
                    yandex_avg_cpa * yandex_convs_for_cpa
                    + vk_avg_cpa * vk_conversions
                    + avito_avg_cpa * avito_conversions
                ) / total_platform_conversions_for_cpa
            else:
                avg_cpa = 0.0
            
            return {
                "costs": costs, 
                "imps": imps, 
                "clks": clks, 
                "convs": convs,
                "avg_cpc": avg_cpc,  # Взвешенное среднее CPC
                "avg_cpa": avg_cpa   # Взвешенное среднее CPA
            }

        # Current period data
        curr = get_data(d_start, d_end)
        
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
        cpa = curr.get("avg_cpa", 0) if curr.get("avg_cpa", 0) > 0 else (curr["costs"] / curr["convs"] if curr["convs"] > 0 else 0)
        ctr = (curr["clks"] / curr["imps"] * 100) if curr["imps"] > 0 else 0
        cr = (curr["convs"] / curr["clks"] * 100) if curr["clks"] > 0 else 0

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

        # CRITICAL: When no campaign_ids, filter by integrations with is_active campaigns
        # to avoid mixing stats from different profiles
        integration_ids_filter = None
        if not campaign_ids and len(client_ids) == 1:
            active_int = db.query(models.Campaign.integration_id).join(
                models.Integration
            ).filter(
                models.Integration.client_id.in_(client_ids),
                models.Campaign.is_active.is_(True)
            ).distinct().all()
            aid_list = [r[0] for r in active_int if r[0]]
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

        def get_metrika_convs(start, end):
            m_q = db.query(
                func.sum(models.MetrikaGoals.conversion_count).label("total")
            ).filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id != "all"
            )

            # Mirror the selected_goals filter from aggregate_summary so Metrika
            # conversions only count goals the user actually configured.
            selected_goal_ids = set()
            for i in db.query(models.Integration).filter(
                models.Integration.client_id.in_(client_ids),
                models.Integration.platform.in_([
                    models.IntegrationPlatform.YANDEX_DIRECT,
                    models.IntegrationPlatform.YANDEX_METRIKA,
                ]),
            ).all():
                if i.selected_goals:
                    try:
                        sg = json.loads(i.selected_goals) if isinstance(i.selected_goals, str) else i.selected_goals
                        selected_goal_ids.update(str(g) for g in (sg or []))
                    except Exception:
                        pass
                if i.primary_goal_id:
                    selected_goal_ids.add(str(i.primary_goal_id))
            if selected_goal_ids:
                synced_goal_ids = {
                    row[0]
                    for row in db.query(models.MetrikaGoals.goal_id)
                    .filter(
                        models.MetrikaGoals.client_id.in_(client_ids),
                        models.MetrikaGoals.goal_id != "all",
                    )
                    .distinct()
                    .all()
                }
                applicable = selected_goal_ids & synced_goal_ids
                if applicable:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(applicable))
                elif synced_goal_ids:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(synced_goal_ids))

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
            if start:
                m_q = m_q.filter(models.MetrikaGoals.date >= start)
            if end:
                m_q = m_q.filter(models.MetrikaGoals.date <= end)
            return int((m_q.scalar() or 0) or 0)

        campaigns = []

        if platform in ["all", "yandex"]:
            y_results = run_yandex_query(d_start, d_end)
            total_metrika_convs = get_metrika_convs(d_start, d_end)
            total_yandex_cost = sum(float(r.cost or 0) for r in y_results)

            # Previous period Yandex data keyed by campaign_id
            prev_y_rows = {}
            prev_total_metrika_convs = 0
            prev_total_yandex_cost = 0
            if prev_start is not None:
                prev_y_list = run_yandex_query(prev_start, prev_end)
                prev_y_rows = {str(r.campaign_id): r for r in prev_y_list}
                prev_total_metrika_convs = get_metrika_convs(prev_start, prev_end)
                prev_total_yandex_cost = sum(float(r.cost or 0) for r in prev_y_list)

            for r in y_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                imps = int(r.impressions or 0)
                # CRITICAL: Конверсии — из Метрики (пропорционально); fallback — Direct
                if total_metrika_convs > 0 and total_yandex_cost > 0:
                    convs = round(total_metrika_convs * (cost / total_yandex_cost))
                else:
                    convs = int(r.conversions or 0)
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
                        prev_convs = int(p.conversions or 0)
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
            a_results = run_avito_query(d_start, d_end)
            prev_a_rows = {}
            if prev_start is not None:
                prev_a_rows = {str(r.campaign_id): r for r in run_avito_query(prev_start, prev_end)}

            for r in a_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = int(r.conversions or 0)
                imps = int(r.impressions or 0)
                cpc = round(cost / clicks, 2) if clicks > 0 else 0
                cpa = round(cost / convs, 2) if convs > 0 else 0
                cid = str(r.campaign_id)
                p = prev_a_rows.get(cid)
                if p:
                    prev_cost = float(p.cost or 0)
                    prev_clicks = int(p.clicks or 0)
                    prev_imps = int(p.impressions or 0)
                    prev_convs = int(p.conversions or 0)
                    prev_cpc = prev_cost / prev_clicks if prev_clicks > 0 else 0
                    prev_cpa = prev_cost / prev_convs if prev_convs > 0 else 0
                else:
                    prev_cost = prev_clicks = prev_imps = prev_convs = prev_cpc = prev_cpa = 0
                disp_name = (r.campaign_display_name or r.campaign_name or "").strip() or "Без названия"
                campaigns.append({
                    "id": cid,
                    "name": f"[AVITO] {disp_name}",
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
            active_int = db.query(models.Campaign.integration_id).join(
                models.Integration
            ).filter(
                models.Integration.client_id.in_(client_ids),
                models.Campaign.is_active.is_(True)
            ).distinct().all()
            aid_list = [r[0] for r in active_int if r[0]]
            if aid_list:
                integration_ids_filter = aid_list

        clicks_result = {str(i): 0 for i in range(7)}
        leads_result = {str(i): 0 for i in range(7)}

        # selected_goal_ids для лидов Yandex (как в aggregate_summary)
        selected_goal_ids = set()
        for i in db.query(models.Integration).filter(
            models.Integration.client_id.in_(client_ids),
            models.Integration.platform.in_([
                models.IntegrationPlatform.YANDEX_DIRECT,
                models.IntegrationPlatform.YANDEX_METRIKA,
            ]),
        ).all():
            if i.selected_goals:
                try:
                    sg = json.loads(i.selected_goals) if isinstance(i.selected_goals, str) else i.selected_goals
                    selected_goal_ids.update(str(g) for g in (sg or []))
                except Exception:
                    pass
            if i.primary_goal_id:
                selected_goal_ids.add(str(i.primary_goal_id))

        integration_ids_for_metrika = None
        if campaign_ids:
            campaign_integrations = db.query(models.Campaign.integration_id).filter(
                models.Campaign.id.in_(campaign_ids)
            ).distinct().all()
            integration_ids_for_metrika = [ci[0] for ci in campaign_integrations if ci[0]]

        if platform in ["all", "yandex"]:
            from sqlalchemy import extract
            # Клики — из YandexStats
            y_rows = db.query(
                extract('dow', models.YandexStats.date).label('dow'),
                func.sum(models.YandexStats.clicks).label('clicks')
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id.in_(client_ids),
                models.Campaign.is_active.is_(True)
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

            # Лиды Yandex — из MetrikaGoals (selected_goals), как в сводке
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
            a_rows = db.query(
                extract('dow', models.AvitoStats.date).label('dow'),
                func.sum(models.AvitoStats.clicks).label('clicks'),
            ).join(models.Campaign, models.AvitoStats.campaign_id == models.Campaign.id).filter(
                models.AvitoStats.client_id.in_(client_ids)
            )
            if campaign_ids:
                a_rows = a_rows.filter(models.Campaign.id.in_(campaign_ids))
            elif integration_ids_filter:
                a_rows = a_rows.filter(models.Campaign.integration_id.in_(integration_ids_filter))
            if d_start:
                a_rows = a_rows.filter(models.AvitoStats.date >= d_start)
            if d_end:
                a_rows = a_rows.filter(models.AvitoStats.date <= d_end)
            a_rows = a_rows.group_by(extract('dow', models.AvitoStats.date)).all()
            for r in a_rows:
                dow = int(r.dow) if r.dow is not None else 0
                clicks_result[str(dow)] = clicks_result.get(str(dow), 0) + int(r.clicks or 0)

        if platform == "avito":
            from sqlalchemy import extract
            m_q = db.query(
                extract('dow', models.MetrikaGoals.date).label('dow'),
                func.sum(models.MetrikaGoals.conversion_count).label('leads')
            ).filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id != "all"
            )
            if selected_goal_ids:
                synced_goal_ids = {
                    row[0]
                    for row in db.query(models.MetrikaGoals.goal_id)
                    .filter(
                        models.MetrikaGoals.client_id.in_(client_ids),
                        models.MetrikaGoals.goal_id != "all",
                    )
                    .distinct()
                    .all()
                }
                applicable = selected_goal_ids & synced_goal_ids
                if applicable:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(applicable))
                elif synced_goal_ids:
                    m_q = m_q.filter(models.MetrikaGoals.goal_id.in_(synced_goal_ids))
            if d_start:
                m_q = m_q.filter(models.MetrikaGoals.date >= d_start)
            if d_end:
                m_q = m_q.filter(models.MetrikaGoals.date <= d_end)
            m_rows = m_q.group_by(extract('dow', models.MetrikaGoals.date)).all()
            for r in m_rows:
                dow = int(r.dow) if r.dow is not None else 0
                leads_result[str(dow)] = leads_result.get(str(dow), 0) + int(r.leads or 0)

        return {"clicks": clicks_result, "leads": leads_result}
