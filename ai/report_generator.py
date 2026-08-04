"""
Генерация AI-отчётов на основе агрегированных данных дашборда.
Использует OpenAI API с поддержкой прокси.
"""
import logging
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy.orm import Session

from core import models, settings
from backend_api.stats_service import StatsService
logger = logging.getLogger(__name__)


def _date_label(value) -> str:
    return value.isoformat() if value else "—"


def _num(value, digits: int = 2) -> float:
    try:
        return round(float(value or 0), digits)
    except (TypeError, ValueError):
        return 0.0


def _create_anthropic_client():
    from anthropic import AsyncAnthropic
    base_url = (getattr(settings, "OPENAI_BASE_URL", "") or "").strip().rstrip("/") or None
    kwargs = {"api_key": settings.OPENAI_API_KEY}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncAnthropic(**kwargs)


# ── AI-комментарий за период: базовый промпт v1.0 (ТЗ admirra_ai_comment_prompt_v1)
COMMENT_PROMPT_VERSION = "v1.2"

# Правило 16 — банлист (регистронезависимо, по основным формам).
_COMMENT_BANLIST = [
    "под знаком", "рывок", "картина", "на фоне", "продемонстрир", "отработал",
    "динамика показала", "ознаменовал", "рухнул", "провален", "обвалил", "взлет",
    "катастроф", "плачевно", "парадоксальн", "драматичн", "впечатляющ",
    "классический сигнал",
]

DASHBOARD_COMMENT_SYSTEM_PROMPT = """Ты — senior трафик-менеджер рекламного агентства. Ты пишешь короткий комментарий к дашборду проекта для коллеги, который ведёт этот проект. Коллега — опытный специалист: он знает механику рекламных систем, видит все цифры на экране перед собой и примет решения сам. Твоя задача — синтез и интерпретация, не пересказ.

## ЧТО ТЫ ПОЛУЧАЕШЬ
JSON с данными проекта за период. Все числа в нём предрасчитаны бэкендом.

## ЧТО ТЫ ВОЗВРАЩАЕШЬ
Только JSON без пояснений и markdown-обёртки:
{"lead": "…", "body": ["…", "…"], "recommendation": "…"}
lead — 1 предложение. body — 1–2 абзаца (для простого периода допустим 1 короткий). recommendation — 1–2 предложения.

## ПРАВИЛА — ДАННЫЕ (нарушение любого = брак)
1. Ты ФОРМУЛИРУЕШЬ, но не ВЫЧИСЛЯЕШЬ. Используй только числа, которые есть в контексте, дословно (допустимо округление процентов до целых). Если числа нет — не упоминай его. Запрещены «оценочно», «порядка», «примерно N».
2. Каждая метрика — со своим числом. Запрещено объединять метрики под общий квалификатор («показы и клики выросли вдвое»).
3. Запрещены кратностные словесные оценки вместо чисел: «вдвое», «на треть», «почти половина». Качественные направления («вырос», «просел») — можно.
4. Малые числа: если лидов за период меньше 20 — проценты изменения дублируй абсолютами («7 лидов против 5»), выводы о тренде не делай, допустимо прямо писать «изменение в пределах шума, судить о тренде рано».
5. Имена кампаний и направлений копируй из контекста посимвольно, в кавычках, без склонений.
6. Дельты, уже видимые в KPI-карточках (расход, показы, клики, лиды, CPC, CPL), в тексте не перечисляй. Цифры в теле — только те, которых нет на экране: CR, разбивка по направлениям, CPA конкретных кампаний, сравнения кампаний.
7. Если в контексте есть comparability_events — сравнение затронутой метрики с прошлым периодом либо не делай, либо явно оговори эффект события. Гипотезы об эффективности на затронутой метрике запрещены.
8. Оценки «приемлемо», «дорого», «в норме» — только относительно target_cpl из контекста. Нет цели — нет оценки, только факт.

## ПРАВИЛА — РЕКОМЕНДАЦИЯ
9. Рекомендация — только действие, доступное трафик-менеджеру: ставки, креативы, аудитории, семантика, включение/отключение кампаний, тест офферов, проверка посадочных, фидов, целей.
10. Перераспределение бюджета между направлениями: directions_mode="fixed" → ЗАПРЕЩЕНО рекомендовать (сравнение направлений допустимо только как факт в теле); directions_mode="flexible" → допустимо, формулируй как предложение.
11. Регистр — предложение, не команда: «стоит рассмотреть…», «проверить…», а не «перераспределить», «немедленно отключить».
12. Если рекомендация может упереться в потолок канала — дай чекпоинт и запасной ход в пределах двух предложений: действие → признак упора → план Б.
13. Если изменения метрик объясняются project_context (заявленной стратегией) — это НЕ проблема и НЕ аномалия. Подавай как ход выполнения решения; рекомендация — про качество исполнения стратегии, не про её откат.

## МЕХАНИКА КАНАЛОВ (учитывай при гипотезах и рекомендациях)
- Поиск ограничен объёмом спроса. Масштабирование — расширение семантики и гео; долив бюджета сверх спроса уходит в рост ставок, не в лиды.
- РСЯ и таргетинг по интересам масштабируются бюджетом, но требуют работы с креативами и аудиториями; аудитории выгорают.
- Свежие кампании проходят обучение; резкие изменения бюджета сбивают его.
- Модель оплаты кампании (bid_strategy) определяет валидные рассуждения: при оплате за конверсии расход = лиды × ставка, клики бесплатны — «слив бюджета на нецелевые клики» невозможен, падение CTR — риск для объёма показов и обучения, не для денег. CPC-логика — только для поскликовой оплаты. Гипотезы про «дорогие клики / пустой трафик» — только для кампаний с bid_strategy="manual_cpc" или "auto_cpc".

## СОГЛАСОВАНИЕ С ЭКРАНОМ
- Флажки детектора: если detector.enabled=true и есть detector.flags — комментарий обязан свести картину с ними. Позитивный вывод при активном алерте по CPL/бюджету должен явно назвать цель и движение к ней («CPL за период снизился до 1 178 ₽ — движение к цели, но выше плановых 1 000 ₽»). Активный флажок игнорировать нельзя: экран не должен говорить двумя голосами.
- НДС: суммы в контексте уже приведены к НДС-режиму экрана (vat_mode) — не пересчитывай их и не упоминай НДС.

## ПРАВИЛА — ЯЗЫК
14. Тон: сухо, декларативно, как сообщение коллеге в рабочий чат. Без метафор, публицистики и эмоций. Серьёзность передаётся цифрами, не лексикой. Числа — в русской типографике: десятичный разделитель запятая (80,07 ₽, 1,94%), тысячи — пробел (2 461 ₽).
15. Лид: вывод простым языком, БЕЗ цифр. Одно простое утверждение — что этот период значит. Запрещены цепочки сравнений.
16. Банлист (не использовать ни в какой форме): «под знаком», «рывок», «картина», «на фоне», «продемонстрировал», «отработал», «динамика показала», «ознаменовался», «рухнул», «провален», «обвалился», «взлетел», «катастрофа», «плачевно», «парадоксальный», «драматичный», «впечатляющий», «классический сигнал».
17. Каждое утверждение — с конкретным референтом: «связки», «сегменты», «качество трафика», «сигнал» без имён кампаний запрещены.
18. Тест «и что?»: каждое предложение должно давать коллеге опору для действия или решения. Предложение без следствия — вычеркни.
19. Не объясняй коллеге азы механики рекламных систем. Механика упоминается только как аргумент конкретной гипотезы.
20. Объём: суммарно 600–900 знаков, жёсткий потолок 1200. Это потолок, не план: простой период — короткий комментарий.
21. Если в контексте есть since_last_visit — это изменения С МОМЕНТА последнего визита коллеги, не за период. Ценность в них: упомяни ключевое (лиды/стоимость заявки с прошлого захода) в ПЕРВОМ предложении тела с числом. Лид при этом остаётся качественным, без цифр (правило 15). Нет since_last_visit — блок не трогай.

## САМОПРОВЕРКА (выполни молча перед ответом)
Сверь черновик: каждое число существует в контексте и совпадает с ним; каждое сравнительное утверждение («сильнее», «слабее», «больше») соответствует числам; лид не противоречит телу и соседние предложения не противоречат друг другу; гипотеза причины не противоречит ни одному числу; при активных флажках детектора картина сведена с ними; рекомендация исполнима по правилам 9–13; банлист-слов нет; длина в лимите. Нашёл нарушение — исправь и проверь снова. Только потом отвечай.

## ПРИМЕРЫ
Контекст: {"period":{"label":"Эта неделя"},"target_cpl":1000,"kpi":{"spend":{"value":45210,"delta_pct":-36},"leads":{"value":18,"delta_pct":-5,"prev_value":19},"cpl":{"value":2512,"delta_pct":-33},"cr_click_to_lead_pct":3.28},"directions_mode":"fixed","campaigns":[{"name":"Поиск / Волгоград","cpa":1537,"leads":18}]}
Ответ: {"lead":"Неделя тише предыдущей, но заявки держатся.","body":["Лидов 18 против 19 — изменение в пределах шума, судить о тренде рано. Заявки идут почти целиком из «Поиск / Волгоград» с CPA 1537 ₽, это ниже целевого CPL. Конверсия из клика в заявку 3,28% — остальные кампании расход тратят, а заявок не дают."],"recommendation":"Стоит проверить посадочные и семантику кампаний без заявок, прежде чем снимать с них бюджет."}

Контекст: {"period":{"label":"Этот месяц"},"target_cpl":2000,"kpi":{"spend":{"value":88000,"delta_pct":12},"leads":{"value":34,"delta_pct":-18},"cpl":{"value":2588,"delta_pct":37},"cr_click_to_lead_pct":1.9},"directions_mode":"flexible","directions":[{"name":"Krasnodar","cpl":1400,"leads":20},{"name":"Rostov","cpl":4100,"leads":6}]}
Ответ: {"lead":"Заявки дорожают: расход растёт, а лидов меньше.","body":["Конверсия в заявку просела до 1,9%. Основной разрыв по направлениям: «Krasnodar» даёт заявку за 1400 ₽, «Rostov» — за 4100 ₽ при целевом CPL 2000 ₽, то есть заметно выше цели именно там."],"recommendation":"Стоит рассмотреть смещение части бюджета из «Rostov» в «Krasnodar» и параллельно проверить офферы «Rostov» — если и после этого CPL не сойдётся к цели, отключить слабые кампании направления."}

Контекст: {"period":{"label":"Эта неделя"},"target_cpl":1000,"kpi":{"leads":{"value":52,"delta_pct":18},"cpl":{"value":1178,"delta_pct":-16},"cr_click_to_lead_pct":4.1},"directions_mode":"fixed","detector":{"enabled":true,"flags":[{"type":"P-2","text":"Стоимость заявки выше цели: 1 178 ₽ при целевом CPL 1 000 ₽"}]},"campaigns":[{"name":"Поиск / Волгоград","cpa":980,"leads":30,"bid_strategy":"auto_cpc"}]}
Ответ: {"lead":"Заявки дешевеют, но цель по стоимости пока не взята.","body":["CPL за период снизился до 1 178 ₽ — движение к цели, но выше плановых 1 000 ₽, флажок по стоимости заявки ещё активен. Конверсия в заявку 4,1%, основной объём даёт «Поиск / Волгоград» с CPA 980 ₽ — ниже цели, на эту кампанию можно опираться."],"recommendation":"Стоит перенести часть недельного бюджета на «Поиск / Волгоград». Если после переноса CPC растёт, а показы нет — спрос по кампании выбран: расширять семантику, а не поднимать ставку."}"""


async def generate_report(
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
    report_type: str = "full",
    folder_id=None,
    platform: str = "all",
    trigger: str = "refresh",
) -> str:
    """
    Генерирует текстовый отчёт на основе данных дашборда.
    report_type: "full" — полный отчёт, "recommendations" — только рекомендации,
    "comment" — короткий клиентский вывод для доставки отчёта.
    """
    if not settings.OPENAI_API_KEY:
        logger.error("generate_report: OPENAI_API_KEY не настроен")
        raise ValueError("OPENAI_API_KEY не настроен")

    if folder_id and not client_id:
        effective_client_ids = StatsService.resolve_folder_client_ids(db, user_id, folder_id)
    else:
        effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        return "Нет доступа к данным проектов."

    try:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    # AI-комментарий за период — отдельный конвейер (промпт v1.1): богатый
    # JSON-контекст, структурный ответ модели, программная пост-валидация.
    if report_type == "dashboard_comment":
        return await _generate_dashboard_comment(
            db, effective_client_ids, d_start, d_end, start_date, end_date, platform or "all", trigger=trigger
        )

    # Собираем контекст
    summary = StatsService.aggregate_summary(
        db, effective_client_ids, d_start, d_end, platform or "all", None, None
    )
    campaigns = StatsService.get_campaign_stats(
        db, effective_client_ids, d_start, d_end, platform or "all", None, None
    )

    # Топ-5 кампаний по конверсиям
    top_campaigns = sorted(
        [c for c in campaigns if c.get("conversions", 0) > 0],
        key=lambda x: x.get("conversions", 0),
        reverse=True,
    )[:5]

    # §6/§7: для короткого дашборд-комментария добавляем факты о подключениях и
    # агрегаты по направлениям — то, что AI иначе домысливает или чего не видит.
    ctx_integrations = None
    ctx_directions = None
    if report_type == "dashboard_comment":
        from core import models as _models
        _plat_ru = {"YANDEX_DIRECT": "Яндекс Директ", "VK_ADS": "VK Реклама", "AVITO_ADS": "Avito Ads", "YANDEX_METRIKA": "Яндекс Метрика"}
        integ_rows = db.query(_models.Integration).filter(_models.Integration.client_id.in_(effective_client_ids)).all()
        ctx_integrations = [
            {
                "name": _plat_ru.get(getattr(i.platform, "value", str(i.platform)), str(i.platform)),
                "status": "подключена" if getattr(i, "connection_status", "active") == "active" else "подключение не завершено",
            }
            for i in integ_rows
        ]
        if len(effective_client_ids) == 1:
            try:
                from backend_api.services import directions as _dir_svc
                client_obj = db.query(_models.Client).filter(_models.Client.id == effective_client_ids[0]).first()
                if client_obj is not None:
                    dstats = _dir_svc.direction_stats(db, client_obj, d_start, d_end, platform or "all")
                    ctx_directions = [
                        {
                            "name": it.get("name"),
                            "expenses": float(it.get("expenses") or 0),
                            "budget_share": float(it.get("budget_share") or 0),
                            "leads": int(it.get("leads") or 0),
                            "cpl": float(it.get("cpl") or 0),
                        }
                        for it in (dstats.get("items") or [])
                    ]
            except Exception as _dir_err:
                logger.warning("dashboard_comment: directions context skipped: %s", _dir_err)

    context = _build_context(summary, top_campaigns, start_date, end_date, ctx_integrations, ctx_directions)

    client = _create_anthropic_client()

    if report_type == "dashboard_comment":
        system_prompt = """Ты — аналитик рекламы. Напиши КОРОТКИЙ комментарий за период к дашборду проекта. Это не отчёт, а выжимка.

Формат — строго четыре элемента, обычным связным текстом на русском:
1) Первая строка — суть периода одним предложением (её мы сами выделим жирным, звёзды не ставь).
2) 1–2 коротких абзаца «что произошло»: синтез и причинно-следственные связи, а не перечисление метрик.
3) Один абзац — вероятная причина.
4) Одна конкретная рекомендация; начни её ровно со слова «Рекомендация:».

Объём 600–900 знаков, жёсткий максимум 1200. Без заголовков, секций, таблиц, списков, эмодзи и любой Markdown-разметки.

Запреты:
- Не переписывай KPI, которые уже видны в карточках дашборда. Ценность — синтез (например: «лиды упали сильнее бюджета — просела эффективность, а не активность»).
- НЕ считай сам. Все дельты, сравнения и производные метрики уже даны в контексте предрасчитанными. Если числа в контексте нет — не пиши про него. Никаких «оценочно», «порядка», «ориентировочно», «~» рядом с цифрами.
- Про интеграции пиши строго по блоку «Подключения»: если канала там нет или он не подключён — так и утверждай, не строй версий «отключена / данные не переданы / требует уточнения».
- Если данных мало — честно скажи это одним предложением, не выдумывай тренды."""
    elif report_type == "comment":
        system_prompt = """Ты — аналитик рекламных кампаний. Сформируй короткий комментарий для клиента к уже готовому отчёту.

Строгие правила:
- ровно 3–5 обычных связных предложений на русском языке;
- без заголовков, таблиц, списков, Markdown и приветствий;
- не переписывай подряд KPI, которые клиент уже видит в карточках;
- назови только существенное изменение или риск, его вероятную причину по данным и одно понятное действие;
- если данных недостаточно, честно скажи это в одном из предложений и не выдумывай причины.
"""
    else:
        system_prompt = """Ты — профессиональный аналитик рекламных кампаний с экспертизой в Яндекс Директ и ВК Реклама.

Твоя задача — анализировать данные и формировать чёткие, структурированные отчёты на русском языке.

## Правила работы с данными

- Всегда опирайся только на предоставленные данные
- Если данных недостаточно для вывода — укажи это явно
- Числа округляй до 2 знаков после запятой, крупные суммы — до целых
- Сравнивай показатели внутри периода (топ/аутсайдеры) и с предыдущим периодом, если он есть

## Ключевые метрики для анализа

Эффективность: CTR, CPC, CPA, CPL, ROAS
Объём: расходы, показы, клики, лиды/конверсии
Качество: процент отказов, глубина просмотра, время на сайте (если доступны)

## Форматирование

- Используй заголовки и короткие абзацы
- Выделяй конкретные цифры: не «высокий CPA», а «CPA 2 340 ₽ (+18% к норме)»
- Топ кампаний оформляй списком с метриками
- Итог — не более 2–3 конкретных выводов"""

    if report_type == "recommendations":
        system_prompt += """

Сфокусируйся исключительно на действиях:
1. Что отключить или снизить бюджет (с обоснованием по метрикам)
2. Что масштабировать (с обоснованием)
3. Что протестировать (конкретные гипотезы)
Каждый пункт — не более 2 предложений. Без общих слов."""
    elif report_type not in ("comment", "dashboard_comment"):
        system_prompt += """

Развёрнутый отчёт. Структура:
1. Общие итоги периода (таблица или список метрик)
2. Динамика vs предыдущий период (если данные есть)
3. Анализ по кампаниям / каналам (Директ vs ВК)
4. Топ-3 лучших и топ-3 худших кампаний
5. Выводы и приоритеты на следующий период"""

    user_message = f"Данные за период {start_date} — {end_date}:\n\n{context}"

    try:
        logger.info("generate_report: calling Anthropic API (model=%s)", settings.OPENAI_MODEL)
        response = await client.messages.create(
            model=settings.OPENAI_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=1.0,
        )
        text = response.content[0].text if response.content else ""
        if report_type == "dashboard_comment":
            result = _sanitize_dashboard_comment(text)
        elif report_type == "comment":
            result = _normalise_delivery_comment(text)
        else:
            result = text.strip()
        if report_type in ("comment", "dashboard_comment") and not result:
            raise ValueError("AI-комментарий пуст")
        logger.info("generate_report: Anthropic returned %d chars", len(result))
        return result
    except Exception as e:
        logger.exception("Anthropic API error: %s", e)
        raise


_PLATFORM_SOURCE = {
    "YANDEX_DIRECT": "yandex_direct",
    "VK_ADS": "vk_ads",
    "AVITO_ADS": "avito_ads",
    "YANDEX_METRIKA": "yandex_metrika",
}


def _build_comment_context(db: Session, effective_client_ids: list, d_start, d_end,
                           start_date: str, end_date: str, platform: str) -> dict:
    """Схема контекста генерации (раздел 2 ТЗ): только предрасчитанные значения."""
    from ai.comment_periods import period_key_for, PERIOD_LABELS

    summary = StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, platform, None, None)
    trends = summary.get("trends") or {}
    single = effective_client_ids[0] if len(effective_client_ids) == 1 else None

    # НДС (§6): дашборд по умолчанию показывает суммы С НДС 22%. Бэк отдаёт
    # расход БЕЗ НДС для Яндекс/VK и С НДС для Avito. Приводим деньги к экрану,
    # иначе комментарий пишет числа, которых на дашборде нет. Дельты — доли,
    # НДС на них не влияет: множим только абсолютные суммы.
    raw_spend = float(summary.get("expenses") or 0)
    cbp = summary.get("cost_by_platform") or {}
    if cbp:
        spend_vat = (float(cbp.get("yandex") or 0) + float(cbp.get("vk") or 0)) * 1.22 + float(cbp.get("avito") or 0)
    else:
        spend_vat = raw_spend * 1.22
    vat_k = (spend_vat / raw_spend) if raw_spend > 0 else 1.22

    def _kpi(value, delta_key, money=False):
        v = _num(float(value or 0) * vat_k) if money else _num(value)
        return {"value": v, "delta_pct": _num(trends.get(delta_key), 1)} if trends else {"value": v}

    leads_val = int(summary.get("leads") or 0)
    kpi = {
        "spend": _kpi(summary.get("expenses"), "expenses", money=True),
        "impressions": {"value": int(summary.get("impressions") or 0), **({"delta_pct": _num(trends.get("impressions"), 1)} if trends else {})},
        "clicks": {"value": int(summary.get("clicks") or 0), **({"delta_pct": _num(trends.get("clicks"), 1)} if trends else {})},
        "cpc": _kpi(summary.get("cpc"), "cpc", money=True),
        "leads": {"value": leads_val, **({"delta_pct": _num(trends.get("leads"), 1)} if trends else {})},
        "cpl": _kpi(summary.get("cpa"), "cpa", money=True),
        "cr_click_to_lead_pct": _num(summary.get("cr")),
    }
    if trends and leads_val:
        d = trends.get("leads")
        if d not in (None, -100) and (1 + d / 100) > 0:
            kpi["leads"]["prev_value"] = int(round(leads_val / (1 + d / 100)))

    # target_cpl — суммарная цель проекта (только для одиночного проекта).
    target_cpl = None
    if single is not None:
        row = (
            db.query(models.ProjectTargetCPA)
            .filter(models.ProjectTargetCPA.client_id == single,
                    models.ProjectTargetCPA.is_summary.is_(True),
                    models.ProjectTargetCPA.control_enabled.is_(True),
                    models.ProjectTargetCPA.target_cpa.isnot(None),
                    models.ProjectTargetCPA.period_start <= d_end,
                    models.ProjectTargetCPA.period_end >= d_start)
            .order_by(models.ProjectTargetCPA.period_start.desc())
            .first()
        )
        if row and row.target_cpa:
            target_cpl = _num(row.target_cpa)

    # Одиночный проект нужен нескольким блокам (направления, режим бюджета,
    # стратегия, детектор) — читаем один раз.
    client_row = db.query(models.Client).filter(models.Client.id == single).first() if single is not None else None

    directions = []
    if client_row is not None:
        try:
            from backend_api.services import directions as _dir_svc
            dstats = _dir_svc.direction_stats(db, client_row, d_start, d_end, platform)
            for it in (dstats.get("items") or []):
                directions.append({
                    "name": it.get("name"),
                    "spend": _num(float(it.get("expenses") or 0) * vat_k),
                    "budget_share_pct": _num(it.get("budget_share"), 1),
                    "leads": int(it.get("leads") or 0),
                    "cpl": _num(float(it.get("cpl") or 0) * vat_k),
                })
        except Exception as _e:
            logger.warning("comment context: directions skipped: %s", _e)

    # Режим бюджета направлений — настройка проекта (правило 10). Если направлений
    # нет — none, иначе берём режим проекта (по умолчанию fixed).
    if not directions:
        directions_mode = "none"
    else:
        directions_mode = getattr(client_row, "directions_budget_mode", None) or "fixed"

    project_context = None
    if client_row is not None:
        sc = (getattr(client_row, "strategy_context", None) or "").strip()
        project_context = sc or None

    campaigns = _comment_campaigns(db, effective_client_ids, d_start, d_end, platform)

    integ_rows = db.query(models.Integration).filter(models.Integration.client_id.in_(effective_client_ids)).all()
    integrations = [
        {
            "source": _PLATFORM_SOURCE.get(getattr(i.platform, "value", str(i.platform)), str(i.platform).lower()),
            "status": "connected" if getattr(i, "connection_status", "active") == "active" else "not_connected",
        }
        for i in integ_rows
    ]

    # Детектор: подмешиваем флажки только если он включён (иначе null).
    detector = None
    if client_row is not None and getattr(client_row, "detector_enabled", False):
        alerts = (
            db.query(models.DetectorAlert)
            .filter(models.DetectorAlert.client_id == single, models.DetectorAlert.status == "open")
            .order_by(models.DetectorAlert.opened_at.desc()).limit(8).all()
        )
        flags = []
        for a in alerts:
            head = str(a.hypothesis_text or "").replace("\r", "").split("\n")[0].lstrip("• ").strip()
            flags.append({"type": (a.meta or {}).get("check") or a.metric, "text": head})
        detector = {"enabled": True, "flags": flags}

    # События, ломающие сравнимость периодов (правило 7): пересекающие период.
    comparability_events = []
    if single is not None:
        ev_rows = (
            db.query(models.ComparabilityEvent)
            .filter(models.ComparabilityEvent.client_id == single,
                    models.ComparabilityEvent.event_date >= d_start,
                    models.ComparabilityEvent.event_date <= d_end)
            .order_by(models.ComparabilityEvent.event_date.desc())
            .all()
        )
        comparability_events = [
            {"type": e.type, "date": e.event_date.isoformat(), "description": e.description or ""}
            for e in ev_rows
        ]

    label = None
    key = period_key_for(start_date, end_date)
    if key:
        label = PERIOD_LABELS.get(key, "").capitalize() or None

    # §9.5: настоящая snapshot-дельта «с последнего просмотра», а не агрегат от
    # даты входа до сегодня. Stats endpoint хранит previous/current и не сдвигает
    # previous на каждом запросе фильтра внутри одного визита.
    since_last_visit = None
    if client_row is not None:
        snapshots = client_row.last_dashboard_snapshot if isinstance(client_row.last_dashboard_snapshot, dict) else {}
        previous = snapshots.get("previous") if isinstance(snapshots.get("previous"), dict) else None
        current = snapshots.get("current") if isinstance(snapshots.get("current"), dict) else None
        if previous and current:
            def _snapshot_metric(key: str, *, money: bool = False) -> dict:
                before = float(previous.get(key) or 0)
                after = float(current.get(key) or 0)
                factor = vat_k if money else 1.0
                delta_pct = None if before == 0 else _num((after - before) / abs(before) * 100, 1)
                return {
                    "previous": _num(before * factor),
                    "current": _num(after * factor),
                    "delta": _num((after - before) * factor),
                    "delta_pct": delta_pct,
                }
            since_last_visit = {
                "since": previous.get("captured_at"),
                "leads": _snapshot_metric("leads"),
                "spend": _snapshot_metric("expenses", money=True),
                "cpl": _snapshot_metric("cpl", money=True),
            }

    context = {
        "period": {"from": start_date, "to": end_date, "label": label},
        "vat_mode": "included_22",
        "target_cpl": target_cpl,
        "kpi": kpi,
        "directions_mode": directions_mode,
        "directions": directions,
        "campaigns": campaigns,
        "integrations": integrations,
        "detector": detector,
        "comparability_events": comparability_events,
        "project_context": project_context,
        "project_age_days": (
            max(0, (datetime.now(timezone.utc).date() - client_row.created_at.date()).days)
            if client_row is not None and getattr(client_row, "created_at", None)
            else None
        ),
    }
    if since_last_visit is not None:
        context["since_last_visit"] = since_last_visit
    memory = getattr(client_row, "ai_comment_memory", None) if client_row is not None else None
    if isinstance(memory, dict) and memory:
        # Не больше одной отсылки к прошлому случаю (§9.5).
        cases = memory.get("cases") if isinstance(memory.get("cases"), list) else None
        if cases is None and any(key in memory for key in ("anomaly", "action", "kpi")):
            cases = [memory]  # миграция старого однообъектного формата на чтении
        previous_case = next((item for item in reversed(cases or []) if isinstance(item, dict)), None)
        if previous_case:
            previous_case = dict(previous_case)
            before = previous_case.get("kpi") if isinstance(previous_case.get("kpi"), dict) else {}
            previous_case["outcome"] = {
                "leads_delta": _num(
                    float((kpi.get("leads") or {}).get("value") or 0)
                    - float(before.get("leads") or 0)
                ),
                "cpl_delta": _num(
                    float((kpi.get("cpl") or {}).get("value") or 0)
                    - float(before.get("cpl") or 0)
                ),
            }
            context["previous_case"] = previous_case
    return context


def data_fingerprint(db: Session, client_ids: list, d_start, d_end, platform: str = "all", include_vat: bool = True) -> str:
    """Отпечаток видимого среза данных периода (§6): по нему фронт понимает,
    что данные изменились после генерации, и показывает «пересчитываем».

    В отпечаток входит и контекст проекта с режимом бюджета — чтобы правка
    «Контекста для AI» тоже помечала комментарий устаревшим и запускала
    регенерацию (§5/§2)."""
    context = _build_comment_context(
        db, client_ids, d_start, d_end, d_start.isoformat(), d_end.isoformat(), platform,
    )
    # Время захвата current snapshot меняется от технического запроса статистики,
    # но не меняет смысл комментария — не включаем его в ключ.
    since = context.get("since_last_visit")
    if isinstance(since, dict):
        since.pop("captured_at", None)
    payload = {
        "project_ids": sorted(str(x) for x in client_ids),
        "period_preset_or_range": context.get("period"),
        "channel_filter": platform,
        "direction_filter": "all",
        "vat_mode": "included_22" if include_vat else "excluded",
        "prompt_version": COMMENT_PROMPT_VERSION,
        "context": context,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _comment_campaigns(db: Session, effective_client_ids: list, d_start, d_end, platform: str) -> list:
    """Усечённый список: топ-10 по расходу + все с лидами (раздел 2)."""
    rows = StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, platform, None, None)
    by_spend = sorted(rows, key=lambda c: float(c.get("cost") or 0), reverse=True)
    picked, seen = [], set()
    for c in by_spend[:10]:
        picked.append(c); seen.add(id(c))
    for c in rows:
        if id(c) not in seen and int(c.get("conversions") or 0) > 0:
            picked.append(c); seen.add(id(c))

    # Все кампании, упомянутые открытыми флажками детектора, обязательны даже
    # без лидов и вне топ-10 (§10.1).
    detector_ids, detector_names = set(), set()
    alerts = db.query(models.DetectorAlert).filter(
        models.DetectorAlert.client_id.in_(effective_client_ids),
        models.DetectorAlert.status == "open",
    ).all()
    for alert in alerts:
        meta = alert.meta if isinstance(alert.meta, dict) else {}
        for key in ("campaign_id", "campaign_external_id"):
            if meta.get(key):
                detector_ids.add(str(meta[key]))
        for value in (meta.get("campaign_ids") or []):
            detector_ids.add(str(value))
        for key in ("campaign_name", "campaign"):
            if meta.get(key):
                detector_names.add(str(meta[key]))
        for value in (meta.get("campaign_names") or []):
            detector_names.add(str(value))
    for c in rows:
        cid = str(c.get("id") or c.get("campaign_id") or c.get("external_id") or "")
        name = str(c.get("name") or c.get("campaign_name") or "")
        if id(c) not in seen and (cid in detector_ids or name in detector_names):
            picked.append(c); seen.add(id(c))

    # Модель оплаты кампании (bid_strategy) — из справочника campaigns по id.
    strategies = {}
    picked_uuids = []
    for c in picked:
        try:
            picked_uuids.append(uuid.UUID(str(c.get("id"))))
        except (ValueError, TypeError, AttributeError):
            continue
    if picked_uuids:
        for cid, bs in (
            db.query(models.Campaign.id, models.Campaign.bid_strategy)
            .filter(models.Campaign.id.in_(picked_uuids), models.Campaign.bid_strategy.isnot(None))
            .all()
        ):
            strategies[str(cid)] = bs

    out = []
    for c in picked:
        leads = int(c.get("conversions") or 0)
        name = c.get("name") or c.get("campaign_name") or "—"
        # НДС по платформе кампании: Avito уже с НДС, Яндекс/VK — добавляем 22%.
        vat = 1.0 if "[Avito]" in name else 1.22
        cost = _num(float(c.get("cost") or 0) * vat)
        item = {
            "name": name,
            "spend": cost,
            "leads": leads,
        }
        bs = strategies.get(str(c.get("id")))
        if bs:
            item["bid_strategy"] = bs
        if c.get("impressions") is not None:
            item["impressions"] = int(c.get("impressions") or 0)
        if c.get("clicks") is not None:
            item["clicks"] = int(c.get("clicks") or 0)
        if c.get("ctr") is not None:
            item["ctr_pct"] = _num(c.get("ctr"))
        if c.get("cpc") is not None:
            item["cpc"] = _num(float(c.get("cpc") or 0) * vat)
        if leads:
            item["cpa"] = _num(cost / leads) if leads else None
        out.append(item)
    return out


def _collect_context_numbers(node, acc: set | None = None) -> set:
    """Множество допустимых числовых значений из контекста (для сверки чисел).

    Числа собираем и из строк тоже (имена кампаний с датами, тексты флажков
    детектора вида «за 7 дней — 3 712 ₽»), иначе легитимные числа из контекста
    ложно помечались как выдуманные."""
    import re
    if acc is None:
        acc = set()
    if isinstance(node, dict):
        for v in node.values():
            _collect_context_numbers(v, acc)
    elif isinstance(node, list):
        for v in node:
            _collect_context_numbers(v, acc)
    elif isinstance(node, bool):
        pass
    elif isinstance(node, (int, float)):
        acc.add(round(abs(float(node))))
    elif isinstance(node, str):
        for tok in re.findall(r"\d[\d\s]*(?:[.,]\d+)?", node):
            norm = re.sub(r"\s", "", tok).replace(",", ".")
            try:
                acc.add(round(abs(float(norm))))
            except ValueError:
                pass
    return acc


def _parse_comment_json(raw: str):
    """Достаём и валидируем схему {lead, body[], recommendation} из ответа."""
    import json, re
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict):
        return None
    lead = obj.get("lead")
    body = obj.get("body")
    rec = obj.get("recommendation")
    if not isinstance(lead, str) or not lead.strip():
        return None
    if isinstance(body, str):
        body = [body]
    if not isinstance(body, list) or not all(isinstance(p, str) for p in body):
        return None
    if not isinstance(rec, str):
        return None
    return {"lead": lead.strip(), "body": [p.strip() for p in body if p and p.strip()], "recommendation": rec.strip()}


def _validate_comment(obj: dict, allowed_numbers: set, directions_fixed: bool, direction_names: list):
    """Пост-валидация (раздел 5). Возвращает (hard, soft) — списки нарушений.

    hard → повтор/фолбэк; soft → допустимо (логируем, длину подрежем)."""
    import re
    hard, soft = [], []
    text = " ".join([obj.get("lead", ""), " ".join(obj.get("body", [])), obj.get("recommendation", "")])
    low = text.lower()

    for term in _COMMENT_BANLIST:
        if term in low:
            hard.append(f"использовано запрещённое слово рядом с «{term}»")
            break

    total = len(obj.get("lead", "")) + sum(len(p) for p in obj.get("body", [])) + len(obj.get("recommendation", ""))
    if total > 1200:
        soft.append(f"длина {total} > 1200")

    rec_low = (obj.get("recommendation", "") or "").lower()
    if directions_fixed and direction_names:
        # Считаем упоминанием направления только имя В КАВЫЧКАХ («Саратов»), а не
        # подстроку — иначе город внутри имени кампании («…Челябинск - авто…»)
        # ложно засчитывался как направление. Реаллокация — только про бюджет:
        # «перенести креативы между кампаниями» это НЕ перелив бюджета.
        named = sum(1 for n in direction_names if n and f"«{n.lower()}»" in rec_low)
        budget_move = (
            "перераспредел" in rec_low
            or "перелит" in rec_low
            or "перелив" in rec_low
            or ("бюджет" in rec_low and any(w in rec_low for w in ("перенес", "перевед", "перевод", "сдвин", "смест", "перекин")))
        )
        if budget_move and named >= 2:
            hard.append("при directions_mode=fixed рекомендован перелив бюджета между направлениями")

    for token in re.findall(r"\d[\d\s]*(?:[.,]\d+)?", text):
        norm = re.sub(r"\s", "", token).replace(",", ".")
        try:
            val = abs(float(norm))
        except ValueError:
            continue
        if val < 100:
            continue
        iv = round(val)
        if not any(abs(iv - a) <= max(1, a * 0.01) for a in allowed_numbers):
            soft.append(f"число {token.strip()} не найдено в контексте")

    return hard, soft


def _flatten_comment(obj: dict, hard_limit: int = 1200) -> str:
    """{lead, body, recommendation} → плоский текст для хранения и фронта."""
    lead = obj.get("lead", "").strip()
    body = [p.strip() for p in obj.get("body", []) if p and p.strip()]
    rec = obj.get("recommendation", "").strip()
    parts = [lead] + body
    if rec:
        parts.append(rec if rec.lower().startswith("рекоменд") else "Рекомендация: " + rec)
    text = "\n\n".join(p for p in parts if p)
    if len(text) > hard_limit:
        cut = text.rfind(". ", 0, hard_limit)
        text = (text[: cut + 1] if cut > hard_limit // 2 else text[:hard_limit]).strip()
    return text


async def _generate_dashboard_comment(db: Session, effective_client_ids: list, d_start, d_end,
                                      start_date: str, end_date: str, platform: str,
                                      trigger: str = "refresh") -> str:
    """Конвейер AI-комментария: контекст → модель (JSON) → пост-валидация → текст."""
    import json
    context = _build_comment_context(db, effective_client_ids, d_start, d_end, start_date, end_date, platform)
    context_json = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    allowed_numbers = _collect_context_numbers(context)
    directions_fixed = context.get("directions_mode") == "fixed"
    direction_names = [d.get("name") for d in (context.get("directions") or [])]

    client = _create_anthropic_client()
    error_hint = ""
    last_obj = None
    last_error = None
    early_mode = context.get("project_age_days") is not None and int(context["project_age_days"]) < 7
    for attempt in range(3):
        user_message = "Контекст:\n" + context_json
        if early_mode:
            user_message += (
                "\n\nРанний режим: истории проекта меньше 7 дней. Сделай текст короче обычного, "
                "не делай выводов о тренде и прямо отделяй отсутствие истории от аномалии."
            )
        if error_hint:
            user_message += "\n\nПредыдущая попытка отклонена: " + error_hint + " Исправь и верни только JSON."
        logger.info("dashboard_comment %s: attempt %d (model=%s)", COMMENT_PROMPT_VERSION, attempt + 1, settings.OPENAI_MODEL)
        started = time.perf_counter()
        try:
            response = await client.messages.create(
                # Кириллица токеноёмкая: до 1200 знаков текста + JSON-обвязка —
                # берём запас, чтобы ответ не обрезался (иначе невалидный JSON).
                model=settings.OPENAI_MODEL,
                max_tokens=2000,
                system=DASHBOARD_COMMENT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.35,
            )
        except Exception as exc:
            last_error = exc
            duration_ms = int((time.perf_counter() - started) * 1000)
            _log_comment_generation(
                db, effective_client_ids, d_start, d_end, "", context, trigger,
                attempt=attempt + 1, retry_count=attempt, validation_failed=True,
                duration_ms=duration_ms, response=None,
            )
            error_hint = "вызов модели завершился технической ошибкой."
            continue
        duration_ms = int((time.perf_counter() - started) * 1000)
        raw = response.content[0].text if response.content else ""
        obj = _parse_comment_json(raw)
        if obj is None:
            _log_comment_generation(
                db, effective_client_ids, d_start, d_end, raw[:1200], context, trigger,
                attempt=attempt + 1, retry_count=attempt, validation_failed=True,
                duration_ms=duration_ms, response=response,
            )
            error_hint = "ответ не является валидным JSON схемы {lead, body[], recommendation}."
            continue
        last_obj = obj
        hard, soft = _validate_comment(obj, allowed_numbers, directions_fixed, direction_names)
        text = _flatten_comment(obj)
        _log_comment_generation(
            db, effective_client_ids, d_start, d_end, text, context, trigger,
            attempt=attempt + 1, retry_count=attempt, validation_failed=bool(hard),
            duration_ms=duration_ms, response=response,
        )
        if not hard:
            if soft:
                logger.warning("dashboard_comment %s: soft issues: %s", COMMENT_PROMPT_VERSION, "; ".join(soft))
            _update_comment_memory(db, effective_client_ids, context, obj)
            return text
        error_hint = " ".join(hard)

    # Повторный провал (раздел 5.5): «устаревший/имперфектный комментарий лучше
    # отсутствующего». Если модель вернула разбираемый JSON — отдаём лучший
    # кандидат (в лог с пометкой), а не 500. Полный отказ — только если модель
    # ни разу не вернула валидный JSON.
    if last_obj is not None:
        logger.warning("dashboard_comment %s: validation_failed, отдаём кандидат (%s)", COMMENT_PROMPT_VERSION, error_hint)
        text = _flatten_comment(last_obj)
        _update_comment_memory(db, effective_client_ids, context, last_obj)
        return text
    if last_error is not None:
        raise last_error
    logger.warning("dashboard_comment %s: модель не вернула валидный JSON", COMMENT_PROMPT_VERSION)
    raise ValueError("AI-комментарий не прошёл валидацию")


def _response_usage(response) -> tuple[int, int, int, int]:
    usage = getattr(response, "usage", None) if response is not None else None
    return (
        int(getattr(usage, "input_tokens", 0) or 0),
        int(getattr(usage, "output_tokens", 0) or 0),
        int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        int(getattr(usage, "cache_read_input_tokens", 0) or 0),
    )


def _model_cost_usd(input_tokens: int, output_tokens: int) -> Decimal:
    """Ставки задаются окружением ProxyAPI, поскольку провайдер может меняться."""
    try:
        input_rate = Decimal(os.getenv("AI_INPUT_COST_PER_MILLION_USD", "0") or "0")
        output_rate = Decimal(os.getenv("AI_OUTPUT_COST_PER_MILLION_USD", "0") or "0")
        return (Decimal(input_tokens) * input_rate + Decimal(output_tokens) * output_rate) / Decimal(1_000_000)
    except Exception:
        return Decimal("0")


def _model_cost_rub(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> Decimal:
    """Фактическая себестоимость ProxyAPI в валюте списания — рублях."""
    try:
        rates = (
            Decimal(os.getenv("AI_INPUT_COST_PER_MILLION_RUB", "774") or "774"),
            Decimal(os.getenv("AI_OUTPUT_COST_PER_MILLION_RUB", "3866") or "3866"),
            Decimal(os.getenv("AI_CACHE_WRITE_COST_PER_MILLION_RUB", "967") or "967"),
            Decimal(os.getenv("AI_CACHE_READ_COST_PER_MILLION_RUB", "78") or "78"),
        )
        tokens = (input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
        return sum(Decimal(value) * rate for value, rate in zip(tokens, rates)) / Decimal(1_000_000)
    except Exception:
        return Decimal("0")


def _log_comment_generation(
    db: Session,
    effective_client_ids: list,
    d_start,
    d_end,
    text: str,
    context: dict,
    trigger: str,
    *,
    attempt: int = 1,
    retry_count: int = 0,
    validation_failed: bool = False,
    duration_ms: int | None = None,
    response=None,
) -> None:
    """§11.2: одна строка на каждый реальный вызов модели, включая ретраи."""
    if not effective_client_ids:
        return
    try:
        pc = context.get("project_context") or ""
        input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens = _response_usage(response)
        db.add(models.AICommentGeneration(
            # Для папочного/сводного комментария схема v1 пока не имеет
            # scope_id, поэтому денежный вызов закрепляем за первым проектом
            # скоупа. Так он всё равно входит в account soft cap и себестоимость.
            client_id=effective_client_ids[0],
            period_from=d_start,
            period_to=d_end,
            trigger=trigger,
            text=text,
            fingerprint=data_fingerprint(db, effective_client_ids, d_start, d_end),
            prompt_version=COMMENT_PROMPT_VERSION,
            model=str(settings.OPENAI_MODEL),
            directions_mode=context.get("directions_mode"),
            vat_mode=context.get("vat_mode"),
            context_hash=hashlib.md5(pc.encode("utf-8")).hexdigest()[:12] if pc else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_tokens,
            cache_read_input_tokens=cache_read_tokens,
            cost_usd=_model_cost_usd(input_tokens, output_tokens),
            cost_rub=_model_cost_rub(
                input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
            ),
            duration_ms=duration_ms,
            campaign_count=len(context.get("campaigns") or []),
            attempt=attempt,
            retry_count=retry_count,
            validation_failed=validation_failed,
        ))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("comment generation log skipped: %s", e)


def _update_comment_memory(db: Session, effective_client_ids: list, context: dict, obj: dict) -> None:
    """Закладывает журнал «аномалия → действие → исход» без вывода мемуаров в UI."""
    if len(effective_client_ids) != 1:
        return
    client = db.query(models.Client).filter(models.Client.id == effective_client_ids[0]).first()
    if not client:
        return
    memory = client.ai_comment_memory if isinstance(client.ai_comment_memory, dict) else {}
    cases = memory.get("cases") if isinstance(memory.get("cases"), list) else None
    if cases is None:
        cases = [memory] if any(key in memory for key in ("anomaly", "action", "kpi")) else []
    cases = [dict(item) for item in cases if isinstance(item, dict)]
    current_kpi = context.get("kpi") or {}
    if cases and isinstance(cases[-1].get("kpi"), dict):
        before = cases[-1]["kpi"]
        cases[-1]["outcome"] = {
            "leads_delta": _num(float((current_kpi.get("leads") or {}).get("value") or 0) - float(before.get("leads") or 0)),
            "cpl_delta": _num(float((current_kpi.get("cpl") or {}).get("value") or 0) - float(before.get("cpl") or 0)),
        }
    flags = ((context.get("detector") or {}).get("flags") or [])[:1]
    cases.append({
        "anomaly": flags[0] if flags else None,
        "action": obj.get("recommendation") or None,
        "outcome": None,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "kpi": {
            "leads": (current_kpi.get("leads") or {}).get("value"),
            "cpl": (current_kpi.get("cpl") or {}).get("value"),
        },
    })
    # Храним квартал ежедневных случаев с запасом; в промпт всё равно попадает
    # только один последний кейс. Ограничение не даёт JSON расти бесконечно.
    client.ai_comment_memory = {"version": 1, "cases": cases[-100:]}
    db.commit()


def _sanitize_dashboard_comment(text: str, hard_limit: int = 1200) -> str:
    """§1/§3: короткий дашборд-комментарий без разметки. Вырезаем markdown,
    оставляем только связный текст (жирный лид фронт делает сам из 1-й строки),
    жёстко ограничиваем длину."""
    import re
    t = (text or "").replace("\r", "")
    t = re.sub(r"(?m)^\s*\|.*\|\s*$", "", t)          # таблицы
    t = re.sub(r"(?m)^\s*-{3,}\s*$", "", t)            # горизонтальные линии ---
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", t)        # заголовки
    t = re.sub(r"(?m)^\s*[-*•]\s+", "", t)             # маркеры списка
    t = re.sub(r"(?m)^\s*\d+[.)]\s+", "", t)           # нумерация
    t = t.replace("**", "").replace("`", "")           # bold/code
    t = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", t)  # *italic*
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) > hard_limit:
        cut = t.rfind(". ", 0, hard_limit)
        t = (t[: cut + 1] if cut > hard_limit // 2 else t[:hard_limit]).strip()
    return t


def _normalise_delivery_comment(text: str) -> str:
    """Keep a short client comment free from Markdown and table formatting."""
    import re
    clean_lines = []
    for line in str(text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"(`{1,3}|\*{1,3}|_{1,3}|~~)", "", line)
        line = line.replace("|", " ")
        if line:
            clean_lines.append(line)
    clean = re.sub(r"\s+", " ", " ".join(clean_lines)).strip()
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    if not 3 <= len(sentences) <= 5:
        return ""
    return " ".join(sentences).strip()


def _build_context(
    summary: dict,
    top_campaigns: list,
    start_date: str,
    end_date: str,
    integrations: list | None = None,
    directions: list | None = None,
) -> str:
    lines = []

    # KPI
    lines.append("## Сводка KPI")
    lines.append(f"Расходы: {summary.get('expenses', 0):,.0f} ₽")
    lines.append(f"Показы: {summary.get('impressions', 0):,}")
    lines.append(f"Клики: {summary.get('clicks', 0):,}")
    lines.append(f"Лиды: {summary.get('leads', 0):,}")
    lines.append(f"CPC: {summary.get('cpc', 0):.2f} ₽")
    lines.append(f"CPA: {summary.get('cpa', 0):.2f} ₽")
    lines.append(f"CTR: {summary.get('ctr', 0):.2f}%")
    lines.append(f"CR: {summary.get('cr', 0):.2f}%")

    trends = summary.get("trends")
    if trends:
        lines.append("\n## Тренды (к прошлому периоду, уже посчитаны — не пересчитывай)")
        lines.append(f"Расходы: {trends.get('expenses', 0):+.1f}%")
        lines.append(f"Показы: {trends.get('impressions', 0):+.1f}%")
        lines.append(f"Клики: {trends.get('clicks', 0):+.1f}%")
        lines.append(f"Лиды: {trends.get('leads', 0):+.1f}%")

    # §6/§7: факты о подключениях — чтобы AI утверждал, а не гадал.
    if integrations is not None:
        lines.append("\n## Подключения (факт, не догадки)")
        if integrations:
            for it in integrations:
                lines.append(f"- {it['name']}: {it['status']}")
        else:
            lines.append("- Нет подключённых рекламных кабинетов")

    # §7: агрегаты по направлениям — синтез, которого нет в отдельных карточках.
    if directions:
        lines.append("\n## Направления за период")
        for d in directions:
            lines.append(
                f"- {d['name']}: расход {d['expenses']:,.0f} ₽ ({d['budget_share']:.0f}% бюджета), "
                f"{d['leads']} лидов, CPL {d['cpl']:,.0f} ₽"
            )

    if top_campaigns:
        lines.append("\n## Топ кампаний по конверсиям")
        for i, c in enumerate(top_campaigns[:5], 1):
            name = c.get("name", c.get("campaign_name", "—"))
            conv = c.get("conversions", 0)
            cost = c.get("cost", 0)
            lines.append(f"{i}. {name}: {conv} лидов, {cost:,.0f} ₽")

    return "\n".join(lines)


def build_assistant_context(
    db: Session,
    user_id: uuid.UUID,
    client_id: uuid.UUID,
    start_date: str,
    end_date: str,
) -> dict:
    effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        raise ValueError("Нет доступа к данным проекта.")

    try:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    summary = StatsService.aggregate_summary(db, effective_client_ids, d_start, d_end, "all", None, None)
    campaigns = StatsService.get_campaign_stats(db, effective_client_ids, d_start, d_end, "all", None, None)

    budgets = (
        db.query(models.ProjectBudget)
        .filter(
            models.ProjectBudget.client_id == client_id,
            models.ProjectBudget.period_start <= d_end,
            models.ProjectBudget.period_end >= d_start,
        )
        .order_by(models.ProjectBudget.channel, models.ProjectBudget.period_start.desc())
        .all()
    )
    targets = (
        db.query(models.ProjectTargetCPA)
        .filter(
            models.ProjectTargetCPA.client_id == client_id,
            models.ProjectTargetCPA.period_start <= d_end,
            models.ProjectTargetCPA.period_end >= d_start,
        )
        .order_by(models.ProjectTargetCPA.channel, models.ProjectTargetCPA.goal_name)
        .all()
    )
    alerts = (
        db.query(models.DetectorAlert)
        .filter(
            models.DetectorAlert.client_id == client_id,
            models.DetectorAlert.status == "open",
        )
        .order_by(models.DetectorAlert.opened_at.desc())
        .limit(10)
        .all()
    )
    integrations = (
        db.query(models.Integration)
        .filter(models.Integration.client_id == client_id)
        .all()
    )

    has_data = any(
        _num(summary.get(key)) > 0
        for key in ("expenses", "impressions", "clicks", "leads", "conversions")
    )
    _client = db.query(models.Client).filter(models.Client.id == client_id).first()
    project_context = ((getattr(_client, "strategy_context", None) or "").strip() or None) if _client else None
    return {
        "period": {"start": start_date, "end": end_date},
        "summary": summary,
        "campaigns": campaigns,
        "budgets": budgets,
        "targets": targets,
        "alerts": alerts,
        "integrations": integrations,
        "has_data": has_data,
        "project_context": project_context,
    }


def assistant_context_to_text(context: dict) -> str:
    summary = context.get("summary") or {}
    campaigns = context.get("campaigns") or []
    budgets = context.get("budgets") or []
    targets = context.get("targets") or []
    alerts = context.get("alerts") or []
    integrations = context.get("integrations") or []

    lines = []
    period = context.get("period") or {}
    lines.append(f"Период: {period.get('start')} — {period.get('end')}")
    if context.get("project_context"):
        lines.append(f"\n## Контекст проекта (заявленные цели/стратегия)\n{context['project_context']}")
    lines.append(f"Подключенные каналы: {', '.join(str(i.platform.value if hasattr(i.platform, 'value') else i.platform) for i in integrations) or 'нет'}")
    lines.append("\n## KPI проекта")
    lines.append(f"Расходы: {_num(summary.get('expenses')):,.2f} ₽")
    lines.append(f"Показы: {int(summary.get('impressions') or 0):,}")
    lines.append(f"Клики: {int(summary.get('clicks') or 0):,}")
    lines.append(f"Конверсии/лиды: {int((summary.get('leads') or summary.get('conversions') or 0) or 0):,}")
    lines.append(f"CPC: {_num(summary.get('cpc')):,.2f} ₽")
    lines.append(f"CPA/CPL: {_num(summary.get('cpa')):,.2f} ₽")
    lines.append(f"CTR: {_num(summary.get('ctr')):.2f}%")
    lines.append(f"CR: {_num(summary.get('cr')):.2f}%")

    trends = summary.get("trends") or {}
    if trends:
        lines.append("\n## Динамика к предыдущему периоду")
        for key, label in (
            ("expenses", "Расходы"),
            ("impressions", "Показы"),
            ("clicks", "Клики"),
            ("leads", "Лиды"),
            ("cpc", "CPC"),
            ("cpa", "CPA/CPL"),
        ):
            if key in trends:
                lines.append(f"{label}: {_num(trends.get(key), 1):+.1f}%")

    if campaigns:
        lines.append("\n## Кампании")
        for c in sorted(campaigns, key=lambda item: (item.get("conversions") or 0, item.get("cost") or 0), reverse=True)[:10]:
            lines.append(
                f"- {c.get('name') or 'Без названия'}: расходы {_num(c.get('cost')):,.2f} ₽, "
                f"клики {int(c.get('clicks') or 0)}, лиды {int(c.get('conversions') or 0)}, "
                f"CPC {_num(c.get('cpc')):,.2f} ₽, CPA/CPL {_num(c.get('cpa')):,.2f} ₽"
            )

    if budgets:
        lines.append("\n## Бюджеты план-факт")
        spent_by_channel = {}
        for c in campaigns:
            name = (c.get("name") or "").lower()
            if "[яд]" in name:
                key = "YANDEX_DIRECT"
            elif "[vk]" in name:
                key = "VK_ADS"
            else:
                key = "OTHER"
            spent_by_channel[key] = spent_by_channel.get(key, 0.0) + _num(c.get("cost"))
        for b in budgets:
            channel = b.channel.value if hasattr(b.channel, "value") else str(b.channel)
            plan = _num(b.amount)
            fact = _num(spent_by_channel.get(channel, 0))
            pct = round((fact / plan) * 100, 1) if plan > 0 else 0
            lines.append(f"- {channel}: план {plan:,.2f} ₽, факт {fact:,.2f} ₽ ({pct:.1f}%), период {_date_label(b.period_start)} — {_date_label(b.period_end)}")

    if targets:
        lines.append("\n## Целевые CPA/CPL")
        for t in targets[:20]:
            channel = t.channel.value if getattr(t, "channel", None) and hasattr(t.channel, "value") else "сводно"
            name = t.goal_name or ("Сводный CPL" if t.is_summary else "Цель без названия")
            enabled = "контроль включен" if t.control_enabled else "контроль выключен"
            lines.append(f"- {channel}: {name}, цель {_num(t.target_cpa):,.2f} ₽, {enabled}")

    if alerts:
        lines.append("\n## Открытые алерты детектора")
        for a in alerts:
            channel = a.channel.value if getattr(a, "channel", None) and hasattr(a.channel, "value") else "проект"
            lines.append(
                f"- {a.severity}, {channel}, {a.metric}: отклонение {_num(a.deviation_pct, 1):+.1f}%, "
                f"факт {_num(a.actual_value)}, база {_num(a.baseline_value)}. "
                f"Гипотеза: {a.hypothesis_text or 'не указана'}"
            )

    if not context.get("has_data"):
        lines.append("\nВажно: по выбранному периоду нет достаточных данных статистики. Не делай выводы о причинах без явного указания на нехватку данных.")

    return "\n".join(lines)


async def chat(
    db: Session,
    user_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
    start_date: str,
    end_date: str,
    user_message: str,
    history: list[dict],
) -> str:
    """
    Отвечает на вопрос пользователя в контексте данных дашборда.
    history: список {role: "user"|"assistant", content: str}
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY не настроен")

    # Чат ассистента всегда привязан к конкретному проекту (роутер требует
    # client_id). Ветки по folder_id в chat() нет — из-за неё падал NameError
    # (folder_id не определён) → все запросы к ассистенту отдавали 503.
    effective_client_ids = StatsService.get_effective_client_ids(db, user_id, client_id)
    if not effective_client_ids:
        return "Нет доступа к данным проектов."

    try:
        d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте YYYY-MM-DD.")

    context = assistant_context_to_text(build_assistant_context(db, user_id, client_id, start_date, end_date))
    client = _create_anthropic_client()

    system_prompt = f"""Ты — аналитик рекламных кампаний. Отвечай на вопросы пользователя на основе данных дашборда.
Данные за период {start_date} — {end_date}:

{context}

Правила:
- Отвечай только по данным из контекста.
- Если данных недостаточно, прямо скажи, каких данных не хватает.
- Не придумывай кампании, цели, бюджеты и причины.
- Не генерируй отчёты и аудиты в чате: для таких запросов скажи, что это отдельный раздел.
- Отвечай кратко, на русском языке, с конкретными числами."""

    messages = []
    for h in (history or []):
        role = h.get("role")
        content = h.get("content") or ""
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.messages.create(
            model=settings.OPENAI_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
            temperature=1.0,
        )
        text = response.content[0].text if response.content else ""
        return text.strip()
    except Exception as e:
        logger.exception("Anthropic API error: %s", e)
        raise
