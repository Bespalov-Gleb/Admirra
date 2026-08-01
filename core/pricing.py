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

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Optional


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
        extra_project_cabinets=3, comments_soft_cap=0,
        white_label=False, recommended=False, visible=True, is_default=True,
    ),
    "agency": PlanSpec(
        code="agency", title="Агентство",
        price_month=6900, price_year=69000,
        projects_limit=10, cabinets_limit=30, users_limit=6, ai_requests_limit=250,
        overflow_allowance_projects=2, overflow_allowance_cabinets=2,
        extra_project_price_month=800, extra_project_price_year=yearly_from_monthly(800),
        extra_project_cabinets=3, comments_soft_cap=0,
        white_label=False, recommended=True, visible=True,
    ),
    "pro": PlanSpec(
        code="pro", title="Про",
        price_month=13900, price_year=139000,
        projects_limit=25, cabinets_limit=75, users_limit=15, ai_requests_limit=700,
        overflow_allowance_projects=3, overflow_allowance_cabinets=2,
        extra_project_price_month=650, extra_project_price_year=yearly_from_monthly(650),
        extra_project_cabinets=3, comments_soft_cap=0,
        white_label=False, recommended=False, visible=True,
    ),
    "white_label": PlanSpec(
        code="white_label", title="White Label",
        price_month=25900, price_year=0,          # WL вне тумблера Месяц/Год (§5.1)
        projects_limit=100, cabinets_limit=300, users_limit=50, ai_requests_limit=2000,
        overflow_allowance_projects=5, overflow_allowance_cabinets=2,
        extra_project_price_month=0, extra_project_price_year=0,   # «по договорённости»
        extra_project_cabinets=3, comments_soft_cap=0,
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


def build_price_book(billing_cfg=None) -> Dict[str, PlanSpec]:
    """Собирает прайс-бук, накладывая переопределения цен из конфига поверх
    дефолтов ТЗ. Если конфиг не передан — читаем актуальный."""
    if billing_cfg is None:
        from core.config import get_config
        billing_cfg = get_config().billing

    book: Dict[str, PlanSpec] = {}
    for code, spec in _BASE_SPECS.items():
        attr = _PRICE_ENV_ATTR.get(code)
        override = getattr(billing_cfg, attr, None) if attr else None
        if override is not None and int(override) != spec.price_month:
            month = int(override)
            book[code] = replace(spec, price_month=month, price_year=yearly_from_monthly(month))
        else:
            book[code] = spec
    return book


def normalize_code(plan_code: Optional[str]) -> str:
    """Приводит код к канону: пустое → start, старые basic/standard → новые."""
    code = (plan_code or DEFAULT_PLAN_CODE).strip().lower()
    return LEGACY_CODE_ALIASES.get(code, code)


def resolve_plan(plan_code: Optional[str], billing_cfg=None) -> PlanSpec:
    """Спека тарифа по коду (с учётом алиасов). Неизвестный код → Старт."""
    book = build_price_book(billing_cfg)
    code = normalize_code(plan_code)
    return book.get(code, book[DEFAULT_PLAN_CODE])


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


def overflow_allowance_projects_for(projects_limit: int) -> int:
    """Формула запаса для НОВЫХ тарифов, не описанных в таблице §4:
    min(5, max(1, ceil(0.2 × projects_limit))). Для четырёх основных берутся
    явные значения из спеки."""
    return min(5, max(1, math.ceil(0.2 * projects_limit)))
