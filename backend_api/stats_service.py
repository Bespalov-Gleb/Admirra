from sqlalchemy.orm import Session
from sqlalchemy import func
from core import models
from datetime import datetime, timedelta
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
    def aggregate_summary(db: Session, client_ids: List[uuid.UUID], d_start: Optional[datetime.date], d_end: datetime.date, platform: str = "all", campaign_ids: Optional[List[uuid.UUID]] = None):
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

            # CRITICAL: Для VK Ads используем взвешенное среднее для CPC и CPA из сохраненных значений
            # Это гарантирует правильный расчет "средняя цена клика" и "средняя цена цели"
            v_q = db.query(
                func.sum(models.VKStats.cost).label("total_cost"),
                func.sum(models.VKStats.impressions).label("total_impressions"),
                func.sum(models.VKStats.clicks).label("total_clicks"),
                func.sum(models.VKStats.conversions).label("total_conversions"),
                # Взвешенное среднее CPC: sum(cpc * clicks) / sum(clicks)
                func.sum(models.VKStats.cpc * models.VKStats.clicks).label("weighted_cpc_sum"),
                # Взвешенное среднее CPA: sum(cpa * conversions) / sum(conversions)
                func.sum(models.VKStats.cpa * models.VKStats.conversions).label("weighted_cpa_sum")
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(client_ids)
            )

            # CRITICAL: Always filter by integration_id to prevent mixing data from different profiles
            # Even when campaigns are not selected, we should only show stats from campaigns
            # that belong to integrations of the selected client_id
            integration_ids = None
            
            if campaign_ids:
                print(f"DEBUG: StatsService.get_data - FILTERING by {len(campaign_ids)} campaigns: {campaign_ids}")
                y_q = y_q.filter(models.Campaign.id.in_(campaign_ids))
                v_q = v_q.filter(models.Campaign.id.in_(campaign_ids))
                
                # Get integration_ids for selected campaigns
                campaign_integrations = db.query(models.Campaign.integration_id).filter(
                    models.Campaign.id.in_(campaign_ids)
                ).distinct().all()
                integration_ids = [ci[0] for ci in campaign_integrations if ci[0]]
                
                if integration_ids:
                    print(f"DEBUG: StatsService.get_data - FILTERING by {len(integration_ids)} integrations from selected campaigns: {integration_ids}")
                    y_q = y_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    v_q = v_q.filter(models.Campaign.integration_id.in_(integration_ids))
            else:
                # When "all campaigns" option is selected on the dashboard,
                # we должны учитывать только кампании, которые пользователь включил в проект (is_active = True).
                # Для отдельных кампаний этот фильтр не нужен, так как они приходят из выпадающего списка уже отфильтрованными.
                y_q = y_q.filter(models.Campaign.is_active.is_(True))
                v_q = v_q.filter(models.Campaign.is_active.is_(True))

                # CRITICAL: When no campaigns selected, filter by all integrations of the client
                # This ensures we don't mix data from different profiles/integrations
                if len(client_ids) == 1:
                    # Get all integrations for this client
                    client_integrations = db.query(models.Integration.id).filter(
                        models.Integration.client_id.in_(client_ids)
                    ).distinct().all()
                    integration_ids = [ci[0] for ci in client_integrations if ci[0]]
                    
                    if integration_ids:
                        print(f"DEBUG: StatsService.get_data - NO campaign filter, but FILTERING by {len(integration_ids)} integrations for client: {integration_ids}")
                        y_q = y_q.filter(models.Campaign.integration_id.in_(integration_ids))
                        v_q = v_q.filter(models.Campaign.integration_id.in_(integration_ids))
                    else:
                        print(f"DEBUG: StatsService.get_data - NO campaign filter, NO integrations found for client {client_ids}")
                else:
                    print(f"DEBUG: StatsService.get_data - NO campaign filter, multiple clients ({len(client_ids)}), showing all integrations")
            
            # Print the actual query for one of them to see the SQL
            # print(f"DEBUG: Y_QUERY: {y_q}")

            # 3. Yandex Metrica Goals
            m_q = db.query(
                func.sum(models.MetrikaGoals.conversion_count).label("total_conversions")
            ).filter(
                models.MetrikaGoals.client_id.in_(client_ids),
                models.MetrikaGoals.goal_id == "all"
            )
            
            # CRITICAL: Filter MetrikaGoals by integration_id when campaigns are selected
            # This ensures we get Metrika data for the same integration as the selected campaigns
            if campaign_ids and integration_ids:
                m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(integration_ids))
            elif not campaign_ids and integration_ids:
                # When "all campaigns" is selected, filter by client's integrations
                m_q = m_q.filter(models.MetrikaGoals.integration_id.in_(integration_ids))

            if start:
                y_q = y_q.filter(models.YandexStats.date >= start)
                v_q = v_q.filter(models.VKStats.date >= start)
                m_q = m_q.filter(models.MetrikaGoals.date >= start)
            if end:
                y_q = y_q.filter(models.YandexStats.date <= end)
                v_q = v_q.filter(models.VKStats.date <= end)
                m_q = m_q.filter(models.MetrikaGoals.date <= end)

            # CRITICAL: Log the date range and integration filter for debugging
            import logging
            debug_logger = logging.getLogger(__name__)
            debug_logger.info(f"🔍 StatsService.get_data - Date range: {start} to {end}")
            debug_logger.info(f"🔍 Integration IDs: {integration_ids}")
            debug_logger.info(f"🔍 Client IDs: {client_ids}")
            debug_logger.info(f"🔍 Campaign IDs: {campaign_ids}")
            
            # CRITICAL: Check what data actually exists in DB for this date range
            if platform in ["all", "yandex"]:
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
            m_s = m_q.first() if platform in ["all", "yandex"] else None # Metrica is usually associated with Yandex

            costs = float((y_s.total_cost if y_s else 0) or 0) + float((v_s.total_cost if v_s else 0) or 0)
            imps = int((y_s.total_impressions if y_s else 0) or 0) + int((v_s.total_impressions if v_s else 0) or 0)
            clks = int((y_s.total_clicks if y_s else 0) or 0) + int((v_s.total_clicks if v_s else 0) or 0)
            
            # Smart Conversion logic: 
            # CRITICAL: Для VK Ads НЕ используем Metrika goals - только conversions из VKStats (vk.goals = Результат)
            # Для Yandex Direct используем Metrika goals если доступны (они более точные), иначе platform conversions
            metrica_convs = int((m_s.total_conversions if m_s else 0) or 0)
            yandex_convs = int((y_s.total_conversions if y_s else 0) or 0)
            vk_convs = int((v_s.total_conversions if v_s else 0) or 0)
            platform_convs = yandex_convs + vk_convs
            
            # CRITICAL: Для VK платформы используем только conversions из VKStats
            if platform == "vk":
                convs = vk_convs
            # Для Yandex или "all" используем Metrika goals если доступны (только для Yandex), иначе platform conversions
            elif platform in ["all", "yandex"]:
                # Используем Metrika goals только если они есть И есть данные от Yandex
                # Если выбрана только VK платформа, Metrika goals не должны использоваться
                if metrica_convs > 0 and yandex_convs > 0:
                    # Для Yandex используем Metrika, для VK - platform conversions
                    convs = metrica_convs + vk_convs
                elif metrica_convs > 0:
                    # Только Metrika (если нет Yandex данных, но есть Metrika - возможно старые данные)
                    convs = metrica_convs
                else:
                    # Используем platform conversions (Yandex + VK)
                    convs = platform_convs
            else:
                # Fallback для других платформ
                convs = platform_convs 
            
            # CRITICAL: Для VK Ads используем взвешенное среднее CPC и CPA из сохраненных значений
            # Это гарантирует правильный расчет "средняя цена клика" и "средняя цена цели"
            vk_clicks = int((v_s.total_clicks if v_s else 0) or 0)
            vk_conversions = int((v_s.total_conversions if v_s else 0) or 0)
            vk_weighted_cpc_sum = float((v_s.weighted_cpc_sum if v_s and v_s.weighted_cpc_sum else 0) or 0)
            vk_weighted_cpa_sum = float((v_s.weighted_cpa_sum if v_s and v_s.weighted_cpa_sum else 0) or 0)
            
            # Взвешенное среднее CPC для VK: sum(cpc * clicks) / sum(clicks)
            vk_avg_cpc = vk_weighted_cpc_sum / vk_clicks if vk_clicks > 0 else 0.0
            # Взвешенное среднее CPA для VK: sum(cpa * conversions) / sum(conversions)
            vk_avg_cpa = vk_weighted_cpa_sum / vk_conversions if vk_conversions > 0 else 0.0
            
            # Для Yandex рассчитываем как обычно
            yandex_clicks = int((y_s.total_clicks if y_s else 0) or 0)
            yandex_conversions = int((y_s.total_conversions if y_s else 0) or 0)
            yandex_cost = float((y_s.total_cost if y_s else 0) or 0)
            yandex_avg_cpc = yandex_cost / yandex_clicks if yandex_clicks > 0 else 0.0
            yandex_avg_cpa = yandex_cost / yandex_conversions if yandex_conversions > 0 else 0.0
            
            # Объединяем CPC и CPA для обеих платформ
            # Если есть данные от обеих платформ, используем взвешенное среднее
            total_clicks_for_cpc = clks
            total_conversions_for_cpa = convs
            
            if total_clicks_for_cpc > 0:
                # Взвешенное среднее CPC: (yandex_cpc * yandex_clicks + vk_cpc * vk_clicks) / total_clicks
                if yandex_clicks > 0 and vk_clicks > 0:
                    avg_cpc = (yandex_avg_cpc * yandex_clicks + vk_avg_cpc * vk_clicks) / total_clicks_for_cpc
                elif yandex_clicks > 0:
                    avg_cpc = yandex_avg_cpc
                elif vk_clicks > 0:
                    avg_cpc = vk_avg_cpc
                else:
                    avg_cpc = 0.0
            else:
                avg_cpc = 0.0
            
            # CRITICAL: Для CPA используем conversions из той же платформы, а не общее количество
            # (которое может включать Metrika goals)
            yandex_convs_for_cpa = int((y_s.total_conversions if y_s else 0) or 0)
            total_platform_conversions_for_cpa = yandex_convs_for_cpa + vk_conversions
            
            if total_platform_conversions_for_cpa > 0:
                # Взвешенное среднее CPA: (yandex_cpa * yandex_conversions + vk_cpa * vk_conversions) / total_platform_conversions
                if yandex_convs_for_cpa > 0 and vk_conversions > 0:
                    avg_cpa = (yandex_avg_cpa * yandex_convs_for_cpa + vk_avg_cpa * vk_conversions) / total_platform_conversions_for_cpa
                elif yandex_convs_for_cpa > 0:
                    avg_cpa = yandex_avg_cpa
                elif vk_conversions > 0:
                    avg_cpa = vk_avg_cpa
                else:
                    avg_cpa = 0.0
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

        # CRITICAL: Используем взвешенное среднее CPC и CPA из get_data
        # Для VK это гарантирует использование значений из API (cpc и vk.cpa)
        # Для Yandex рассчитываем как обычно (costs/clicks и costs/conversions)
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
    def get_campaign_stats(db: Session, client_ids: List[uuid.UUID], d_start: Optional[datetime.date], d_end: datetime.date, platform: str = "all", campaign_ids: Optional[List[uuid.UUID]] = None):
        if not client_ids:
            return []

        campaigns = []

        if platform in ["all", "yandex"]:
            y_query = db.query(
                models.Campaign.id.label("campaign_id"),
                models.YandexStats.campaign_name,
                func.sum(models.YandexStats.impressions).label("impressions"),
                func.sum(models.YandexStats.clicks).label("clicks"),
                func.sum(models.YandexStats.cost).label("cost"),
                func.sum(models.YandexStats.conversions).label("conversions")
            ).join(models.Campaign, models.YandexStats.campaign_id == models.Campaign.id).filter(
                models.YandexStats.client_id.in_(client_ids)
                # CRITICAL: Removed is_active filter - statistics should be shown for all campaigns
                # is_active is a user selection flag, not a data filtering flag
            )

            if campaign_ids:
                y_query = y_query.filter(models.Campaign.id.in_(campaign_ids))

            if d_start:
                y_query = y_query.filter(models.YandexStats.date >= d_start)
            if d_end:
                y_query = y_query.filter(models.YandexStats.date <= d_end)

            y_results = y_query.group_by(models.Campaign.id, models.YandexStats.campaign_name).all()
            for r in y_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = int(r.conversions or 0)
                campaigns.append({
                    "id": str(r.campaign_id),
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
                models.Campaign.id.label("campaign_id"),
                models.VKStats.campaign_name,
                func.sum(models.VKStats.impressions).label("impressions"),
                func.sum(models.VKStats.clicks).label("clicks"),
                func.sum(models.VKStats.cost).label("cost"),
                func.sum(models.VKStats.conversions).label("conversions")
            ).join(models.Campaign, models.VKStats.campaign_id == models.Campaign.id).filter(
                models.VKStats.client_id.in_(client_ids)
                # CRITICAL: Removed is_active filter - statistics should be shown for all campaigns
                # is_active is a user selection flag, not a data filtering flag
            )

            if campaign_ids:
                v_query = v_query.filter(models.Campaign.id.in_(campaign_ids))

            if d_start:
                v_query = v_query.filter(models.VKStats.date >= d_start)
            if d_end:
                v_query = v_query.filter(models.VKStats.date <= d_end)

            v_results = v_query.group_by(models.Campaign.id, models.VKStats.campaign_name).all()
            for r in v_results:
                cost = float(r.cost or 0)
                clicks = int(r.clicks or 0)
                convs = int(r.conversions or 0)
                campaigns.append({
                    "id": str(r.campaign_id),
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
