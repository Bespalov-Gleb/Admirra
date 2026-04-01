"""
Маппинг типов целевых действий (типы ЦД) VK Рекламы на русские названия.

API возвращает коды (leadads, socialengagement, traffic и т.д.) — переводим на русский.
Источники: Package.objective, AdPlan.objective, типы кампаний.
"""

# Маппинг кодов типов ЦД VK Ads API → русское название
VK_GOAL_ACTION_RU: dict[str, str] = {
    # Типы ЦД из API (leadads, socialengagement и т.д.)
    "leadads": "Лид-формы",
    "socialengagement": "Действия в социальных сетях",
    # Конверсии (Package.objective)
    "traffic": "Трафик",
    "appinstalls": "Установки приложений",
    "app_install": "Установки приложений",
    "app_installs": "Установки приложений",
    "reengagement": "Ремаркетинг в приложение",
    "playersengagement": "Привлечение игроков в соц. игры",
    "videoviews": "Просмотр видео",
    "video_views": "Просмотр видео",
    "storeproductssales": "Покупки в интернет-магазине",
    "store_products_sales": "Покупки в интернет-магазине",
    "engagement": "Конверсии",
    "articleviews": "Просмотр статей",
    "article_views": "Просмотр статей",
    "social_engagement": "Действия в социальных сетях",
    "storevisits": "Посещение точек продаж",
    "store_visits": "Посещение точек продаж",
    "lead_forms": "Лид-формы",
    "leadforms": "Лид-формы",
    "community": "Вступление в сообщество",
    "group_join": "Вступление в сообщество",
    # Узнаваемость (охват)
    "reach": "Охват",
    "audiolistening": "Аудиореклама",
    "audio_listening": "Аудиореклама",
    "premium_reach": "Охват в премиальной сети",
    "premium_reach_network": "Охват в премиальной сети",
    "general_ttm": "Медийные размещения",
    # Дополнительные (из практики)
    "branding": "Медийная реклама",
    "catalogue": "Каталог товаров",
    "catalogue_sales": "Продажи из каталога",
    "mini_app": "Мини-приложения",
    "profile": "Продвижение профиля",
    "dzen": "Дзен",
    # Детализация по priced_event_type из документации Package:
    # 41 — события в Сообществах VK, 43 — in-app события VK Mini Apps, 51 — лидформы.
    "evt_41_community_actions": "Подписка на сообщество",
    "evt_43_miniapp_events": "Запуск miniapp приложения",
    "evt_51_lead_forms": "Лид-формы",
}


def get_vk_goal_action_name_ru(code: str) -> str:
    """
    Возвращает русское название целевого действия по коду VK.
    Если код неизвестен — возвращает очищенный код (без скобок и точек).
    """
    if not code or not isinstance(code, str):
        return code or ""
    code_clean = code.strip().lower().replace("(", "").replace(")", "").replace(".", "")
    return VK_GOAL_ACTION_RU.get(code_clean, code.strip())
