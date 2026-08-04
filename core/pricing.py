"""Единый прайс-бук (§7 ТЗ «Экономика продукта»).

Один источник истины по тарифам: коды, названия, цены, лимиты, запас сверх
лимита и параметры докупки слотов. Раньше это было размазано по конфигу и
двум местам с захардкоженными кабинетами (`subscription.py`, `billing.py`) —
теперь всё живёт здесь.

Цены оставлены переопределяемыми через существующие env-переменные
(`BILLING_PLAN_*_PRICE_RUB`), поэтому на проде продолжают действовать тестовые
суммы, пока их не заменят на боевые. Лимиты, овераж и докупка — значения новой
линейки из ТЗ, заданные константами.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Dict, List, Mapping, Optional


# Версия прайс-бука. Пишется в аккаунт при подписке (`price_book_version`) и даёт
# зафиксировать цену за клиентом при будущих изменениях линейки (§7.2). Любое
# изменение ЦЕН или структуры линейки — повод поднять версию.
PRICE_BOOK_VERSION = 1

# Годовая скидка (§4.1): 17%, в интерфейсе — «два месяца в подарок».
YEARLY_DISCOUNT = 0.17

# Старые коды тарифов → новые. В БД у тестовых аккаунтов ещё basic/standard;
# резолвер понимает их до миграции §7.3.
LEGACY_CODE_ALIASES: Dict[str, str] = {"basic": "agency", "standard": "pro"}

DEFAULT_PLAN_CODE = "start"


@dataclass(frozen=True)
class PlanSpec:
    """Строка прайс-бука. Все поля §7.1."""

    code: str
    title: str
    price_month: int
    price_year: int
    projects_limit: int
    cabinets_limit: int
    users_limit: int
    ai_requests_limit: int
    overflow_allowance_projects: int
    overflow_allowance_cabinets: int
    extra_project_price_month: int
    extra_project_price_year: int
    extra_project_cabinets: int
    max_extra_project_slots: int
    comments_soft_cap: int           # 0 → вычисляется как projects_limit * 30 (§9.4)
    white_label: bool = False
    recommended: bool = False
    visible: bool = True
    is_default: bool = False

    @property
    def effective_comments_soft_cap(self) -> int:
        return self.comments_soft_cap or self.projects_limit * 30


def yearly_from_monthly(month: int) -> int:
    """Годовая цена из месячной: −17% (§4.1). Без округления до тысячи, иначе
    маленькие тестовые суммы (20 ₽/мес) схлопывались бы в 0. У реальных тарифов
    годовые заданы явно (29000/69000/139000) прямо в спеке."""
    if month <= 0:
        return 0
    return int(round(month * 12 * (1 - YEARLY_DISCOUNT)))


# Базовая линейка (§4). Цены здесь — дефолты ТЗ; фактические значения могут быть
# переопределены из конфига (см. build_price_book). Запас проектов — из таблицы
# §4 (1/2/3/5); запас кабинетов — фиксированные +2 (§8.3); слот даёт +3 кабинета
# и +1 проект (§8.2).
_BASE_SPECS: Dict[str, PlanSpec] = {
    "start": PlanSpec(
        code="start", title="Старт",
        price_month=2900, price_year=29000,
        projects_limit=3, cabinets_limit=9, users_limit=2, ai_requests_limit=50,
        overflow_allowance_projects=1, overflow_allowance_cabinets=2,
        extra_project_price_month=1100, extra_project_price_year=yearly_from_monthly(1100),
        extra_project_cabinets=3, max_extra_project_slots=3, comments_soft_cap=0,
        white_label=False, recommended=False, visible=True, is_default=True,
    ),
    "agency": PlanSpec(
        code="agency", title="Агентство",
        price_month=6900, price_year=69000,
        projects_limit=10, cabinets_limit=30, users_limit=6, ai_requests_limit=250,
        overflow_allowance_projects=2, overflow_allowance_cabinets=2,
        extra_project_price_month=800, extra_project_price_year=yearly_from_monthly(800),
        extra_project_cabinets=3, max_extra_project_slots=8, comments_soft_cap=0,
        white_label=False, recommended=True, visible=True,
    ),
    "pro": PlanSpec(
        code="pro", title="Про",
        price_month=13900, price_year=139000,
        projects_limit=25, cabinets_limit=75, users_limit=15, ai_requests_limit=700,
        overflow_allowance_projects=3, overflow_allowance_cabinets=2,
        extra_project_price_month=650, extra_project_price_year=yearly_from_monthly(650),
        extra_project_cabinets=3, max_extra_project_slots=10, comments_soft_cap=0,
        white_label=False, recommended=False, visible=True,
    ),
    "white_label": PlanSpec(
        code="white_label", title="White Label",
        price_month=25900, price_year=0,          # WL вне тумблера Месяц/Год (§5.1)
        projects_limit=100, cabinets_limit=300, users_limit=50, ai_requests_limit=2000,
        overflow_allowance_projects=5, overflow_allowance_cabinets=2,
        extra_project_price_month=0, extra_project_price_year=0,   # «по договорённости»
        extra_project_cabinets=3, max_extra_project_slots=0, comments_soft_cap=0,
        white_label=True, recommended=False, visible=True,
    ),
}

# Какая env-цена конфигурации отвечает за какой новый код (сохраняем боевые
# тестовые суммы на проде: start/basic/standard = 10/20/30).
_PRICE_ENV_ATTR: Dict[str, str] = {
    "start": "plan_start_price_rub",
    "agency": "plan_basic_price_rub",
    "pro": "plan_standard_price_rub",
}

# Цена докупаемого слота — тоже переопределяема (§8.1), чтобы на проде поставить
# тестовый минимум для проверки оплаты.
_SLOT_PRICE_ENV_ATTR: Dict[str, str] = {
    "start": "slot_price_start_rub",
    "agency": "slot_price_agency_rub",
    "pro": "slot_price_pro_rub",
}


def build_price_book(billing_cfg=None) -> Dict[str, PlanSpec]:
    """Собирает прайс-бук, накладывая переопределения цен из конфига поверх
    дефолтов ТЗ. Если конфиг не передан — читаем актуальный."""
    if billing_cfg is None:
        from core.config import get_config
        billing_cfg = get_config().billing

    raw_price_book = getattr(billing_cfg, "price_book_json", "") or ""
    configured_plans: Mapping[str, Any] = {}
    if raw_price_book:
        try:
            parsed = json.loads(raw_price_book)
        except (TypeError, ValueError) as exc:
            raise ValueError("BILLING_PRICE_BOOK_JSON must be valid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise ValueError("BILLING_PRICE_BOOK_JSON must contain an object")
        candidate = parsed.get("plans", parsed)
        if not isinstance(candidate, Mapping):
            raise ValueError("BILLING_PRICE_BOOK_JSON.plans must contain an object")
        configured_plans = candidate

    allowed_fields = {item.name for item in fields(PlanSpec)}
    book: Dict[str, PlanSpec] = {}
    for code, spec in _BASE_SPECS.items():
        updated = spec
        # Переопределение цены тарифа.
        attr = _PRICE_ENV_ATTR.get(code)
        override = getattr(billing_cfg, attr, None) if attr else None
        if override is not None and int(override) != spec.price_month:
            month = int(override)
            updated = replace(updated, price_month=month, price_year=yearly_from_monthly(month))
        # Переопределение цены слота.
        slot_attr = _SLOT_PRICE_ENV_ATTR.get(code)
        slot_override = getattr(billing_cfg, slot_attr, None) if slot_attr else None
        if slot_override is not None and int(slot_override) != spec.extra_project_price_month:
            sp = int(slot_override)
            updated = replace(updated, extra_project_price_month=sp, extra_project_price_year=yearly_from_monthly(sp))
        override_spec = configured_plans.get(code)
        if override_spec is not None:
            if not isinstance(override_spec, Mapping):
                raise ValueError(f"Price-book plan '{code}' must contain an object")
            unknown = set(override_spec) - allowed_fields
            if unknown:
                raise ValueError(f"Unknown fields for plan '{code}': {', '.join(sorted(unknown))}")
            values = {**asdict(updated), **dict(override_spec), "code": code}
            updated = PlanSpec(**values)
        book[code] = updated
    return book


def current_price_book_version(billing_cfg=None) -> int:
    """Версия активного конфигурационного прайс-бука."""
    if billing_cfg is None:
        from core.config import get_config
        billing_cfg = get_config().billing
    raw = getattr(billing_cfg, "price_book_json", "") or ""
    if not raw:
        return PRICE_BOOK_VERSION
    try:
        parsed = json.loads(raw)
        return max(1, int(parsed.get("version", PRICE_BOOK_VERSION))) if isinstance(parsed, Mapping) else PRICE_BOOK_VERSION
    except (TypeError, ValueError):
        # build_price_book выдаст понятную ошибку при фактическом чтении линейки.
        return PRICE_BOOK_VERSION


def normalize_code(plan_code: Optional[str]) -> str:
    """Приводит код к канону: пустое → start, старые basic/standard → новые."""
    code = (plan_code or DEFAULT_PLAN_CODE).strip().lower()
    return LEGACY_CODE_ALIASES.get(code, code)


def resolve_plan(plan_code: Optional[str], billing_cfg=None) -> PlanSpec:
    """Спека тарифа по коду (с учётом алиасов). Неизвестный код → Старт."""
    book = build_price_book(billing_cfg)
    code = normalize_code(plan_code)
    return book.get(code, book[DEFAULT_PLAN_CODE])


def resolve_plan_strict(plan_code: Optional[str], billing_cfg=None) -> PlanSpec:
    """Спека тарифа для публичных API: неизвестный код — ошибка, не Start.

    Мягкий ``resolve_plan`` оставлен для чтения старых строк БД, но принимать
    пользовательский ввод через него нельзя: опечатка раньше молча превращалась
    в покупку/лимиты Start.
    """
    book = build_price_book(billing_cfg)
    code = normalize_code(plan_code)
    if code not in book:
        raise ValueError(f"Unknown plan code: {plan_code}")
    return book[code]


def plan_snapshot(spec: PlanSpec) -> Dict[str, Any]:
    """Неизменяемый снимок строки прайс-бука для конкретной подписки."""
    return {**asdict(spec), "_price_book_version": current_price_book_version()}


def plan_from_snapshot(snapshot: Optional[Mapping[str, Any]], fallback: PlanSpec) -> PlanSpec:
    """Восстанавливает строку прайс-бука из БД с безопасным fallback.

    Новые поля могут появляться после сохранения снимка, поэтому недостающие
    значения берём из актуальной спеки того же тарифа.
    """
    if not isinstance(snapshot, Mapping):
        return fallback
    allowed = {item.name for item in fields(PlanSpec)}
    values = {**asdict(fallback), **{k: v for k, v in snapshot.items() if k in allowed}}
    if normalize_code(values.get("code")) != fallback.code:
        return fallback
    try:
        return PlanSpec(**values)
    except (TypeError, ValueError):
        return fallback


def list_plans(*, visible_only: bool = True, billing_cfg=None) -> List[PlanSpec]:
    """Линейка по порядку. visible_only=False отдаёт и снятые с продажи тарифы
    (для аккаунтов, что на них сидят)."""
    book = build_price_book(billing_cfg)
    order = ["start", "agency", "pro", "white_label"]
    plans = [book[c] for c in order if c in book]
    if visible_only:
        plans = [p for p in plans if p.visible]
    return plans


def cabinet_limit_for_plan(plan_code: Optional[str], billing_cfg=None) -> int:
    return resolve_plan(plan_code, billing_cfg).cabinets_limit


# Порядок тарифов для апгрейда/паритета. White Label — по заявке, в лестницу
# докупки не входит.
PLAN_LADDER = ["start", "agency", "pro", "white_label"]


def next_plan_code(plan_code: Optional[str]) -> Optional[str]:
    """Следующий по старшинству тариф или None (для Про следующий — WL по заявке)."""
    code = normalize_code(plan_code)
    if code in PLAN_LADDER:
        i = PLAN_LADDER.index(code)
        if i + 1 < len(PLAN_LADDER):
            return PLAN_LADDER[i + 1]
    return None


def slots_until_parity(plan_code: Optional[str], purchased_slots: int = 0, billing_cfg=None) -> int:
    """Сколько ещё слотов можно докупить, пока это выгоднее следующего тарифа
    (§8.1): докупать можно, пока цена тарифа + N × цена слота < цена следующего.
    Возвращает остаток от текущего числа докупленных слотов. 0 — паритет достигнут
    или докупка не имеет смысла (нет следующего тарифа / нулевая цена слота)."""
    spec = resolve_plan(plan_code, billing_cfg)
    # Лимит фиксируется продуктовой матрицей, а не тестовой env-ценой. Иначе при
    # checkout 10/20/30 ₽ количество слотов самопроизвольно менялось, а Pro
    # вообще получал 0 из-за следующего заявочного White Label.
    max_slots = max(0, int(spec.max_extra_project_slots or 0))
    return max(0, max_slots - int(purchased_slots or 0))


def overflow_allowance_projects_for(projects_limit: int) -> int:
    """Формула запаса для НОВЫХ тарифов, не описанных в таблице §4:
    min(5, max(1, ceil(0.2 × projects_limit))). Для четырёх основных берутся
    явные значения из спеки."""
    return min(5, max(1, math.ceil(0.2 * projects_limit)))
