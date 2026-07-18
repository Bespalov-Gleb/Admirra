"""
Маппинг типов целевых действий (типы ЦД) VK Рекламы на русские названия.

API возвращает коды (leadads, socialengagement, traffic и т.д.) — переводим на русский.
Источники: Package.objective, AdPlan.objective, типы кампаний.
"""

# Маппинг кодов типов ЦД VK Ads API → русское название.
# ВАЖНО: разные технические коды (особенно для лид-форм) должны иметь РАЗНЫЕ русские названия,
# чтобы в UI не было нескольких разных vk_goal_action_id с одинаковым vk_goal_action_name.
VK_GOAL_ACTION_RU: dict[str, str] = {
    # Типы ЦД из API (leadads, socialengagement и т.д.) — групповые цели верхнего уровня
    "leadads": "Лид-формы (группа)",
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
    "site_conversions": "Конверсии на сайте",
    "siteconversions": "Конверсии на сайте",
    "site_conversion": "Конверсии на сайте",
    "conversions": "Конверсии на сайте",
    "messages": "Сообщения",
    "vkmessages": "Сообщения",
    "leadgen": "Лид-формы (группа)",
    "articleviews": "Просмотр статей",
    "article_views": "Просмотр статей",
    "social_engagement": "Действия в социальных сетях",
    "storevisits": "Посещение точек продаж",
    "store_visits": "Посещение точек продаж",
    "lead_forms": "Лид-формы (группа)",
    "leadforms": "Лид-формы (группа)",
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
    # 41 — события в Сообществах VK, 43 — in-app события VK Mini Apps, 51 — лид-формы.
    "evt_41_community_actions": "Подписка на сообщество",
    "evt_43_miniapp_events": "Запуск miniapp приложения",
    # Для лид-форм даём отдельное атомарное действие, а не групповое название
    "evt_51_lead_forms": "Отправка лид-формы",
}


def _clean_code(code: str) -> str:
    """Нормализует код ЦД: lower, без скобок/точек/пробелов по краям."""
    if not code or not isinstance(code, str):
        return ""
    return code.strip().lower().replace("(", "").replace(")", "").replace(".", "")


def get_vk_goal_action_name_ru(code: str) -> str:
    """
    Возвращает русское название целевого действия по коду VK.
    Если код неизвестен — возвращает очищенный код (без скобок и точек).
    """
    if not code or not isinstance(code, str):
        return code or ""
    code_clean = _clean_code(code)
    return VK_GOAL_ACTION_RU.get(code_clean, code.strip())


# Категории типов ЦД. Нужны, чтобы в блоке «Целевые действия» НЕ суммировать
# несовместимые типы: лиды (lead) — это результат-заявка и их можно складывать
# как «лиды»; трафик/охват/просмотры — это другие единицы, их нельзя суммировать
# с лидами в один итог. summable=True только для категории lead.
VK_GOAL_ACTION_CATEGORY: dict[str, str] = {
    # ——— Лиды (результат-заявка) — суммируемые ———
    "leadads": "lead",
    "lead_forms": "lead",
    "leadforms": "lead",
    "leadgen": "lead",
    "evt_51_lead_forms": "lead",
    "site_conversions": "lead",
    "siteconversions": "lead",
    "site_conversion": "lead",
    "conversions": "lead",
    "engagement": "lead",
    "messages": "lead",
    "vkmessages": "lead",
    "storeproductssales": "lead",
    "store_products_sales": "lead",
    "catalogue_sales": "lead",
    # ——— Социальные действия / подписки (отдельная категория, не лид) ———
    "socialengagement": "engagement",
    "social_engagement": "engagement",
    "evt_41_community_actions": "engagement",
    "community": "engagement",
    "group_join": "engagement",
    "playersengagement": "engagement",
    "profile": "engagement",
    # ——— Установки/мини-приложения ———
    "appinstalls": "install",
    "app_install": "install",
    "app_installs": "install",
    "reengagement": "install",
    "mini_app": "install",
    "evt_43_miniapp_events": "install",
    # ——— Трафик ———
    "traffic": "traffic",
    # ——— Охват / медийка ———
    "reach": "reach",
    "premium_reach": "reach",
    "premium_reach_network": "reach",
    "general_ttm": "reach",
    "branding": "reach",
    "audiolistening": "reach",
    "audio_listening": "reach",
    # ——— Просмотры контента ———
    "videoviews": "views",
    "video_views": "views",
    "articleviews": "views",
    "article_views": "views",
    "storevisits": "views",
    "store_visits": "views",
    "dzen": "views",
}

# Русские подписи категорий для UI.
VK_CATEGORY_LABEL_RU: dict[str, str] = {
    "lead": "Лиды",
    "engagement": "Действия в сообществах",
    "install": "Установки и мини-приложения",
    "traffic": "Трафик",
    "reach": "Охват",
    "views": "Просмотры",
    "other": "Другие действия",
}


def get_vk_goal_action_category(code: str) -> str:
    """Категория типа ЦД VK (lead/engagement/install/traffic/reach/views/other)."""
    if not code or not isinstance(code, str):
        return "other"
    code_clean = code.strip().lower().replace("(", "").replace(")", "").replace(".", "")
    return VK_GOAL_ACTION_CATEGORY.get(code_clean, "other")


def is_vk_lead_action(code: str) -> bool:
    """True, если тип ЦД считается лидом (результат-заявка) и его можно суммировать."""
    return get_vk_goal_action_category(code) == "lead"

# Коды лид-форм (однозначно лидовая семантика). Используются ТОЛЬКО для автодефолта
# при подключении кабинета: по ТЗ автоматически лидовыми отмечаются лишь лид-формы,
# остальные лидовые типы (сообщения, конверсии на сайте, продажи каталога и т.п.)
# агентство выбирает само в настройках интеграции.
VK_LEAD_FORM_CODES: set[str] = {
    "leadads", "lead_forms", "leadforms", "leadgen", "evt_51_lead_forms",
}


def is_vk_lead_form(code: str) -> bool:
    """True только для лид-форм — для автодефолта состава лидов при подключении."""
    if not code or not isinstance(code, str):
        return False
    return _clean_code(code) in VK_LEAD_FORM_CODES
