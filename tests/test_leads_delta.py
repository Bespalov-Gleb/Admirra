"""ТЗ «Дельта по заявкам» §3: матрица предыдущих сопоставимых периодов."""
from datetime import date

from backend_api.stats import resolve_previous_period


def test_today_compares_with_full_yesterday():
    assert resolve_previous_period(date(2026, 7, 10), date(2026, 7, 10), "today") == (date(2026, 7, 9), date(2026, 7, 9))


def test_yesterday_compares_with_day_before():
    assert resolve_previous_period(date(2026, 7, 9), date(2026, 7, 9), "yesterday") == (date(2026, 7, 8), date(2026, 7, 8))


def test_this_week_compares_to_date_not_adjacent():
    # Пн 06.07 – пт 10.07 → пн–пт прошлой недели, а не «встык 5 дней»
    assert resolve_previous_period(date(2026, 7, 6), date(2026, 7, 10), "this_week") == (date(2026, 6, 29), date(2026, 7, 3))


def test_last_week_is_adjacent_full_week():
    assert resolve_previous_period(date(2026, 6, 29), date(2026, 7, 5), "last_week") == (date(2026, 6, 22), date(2026, 6, 28))


def test_this_month_same_day_count_from_month_start():
    assert resolve_previous_period(date(2026, 7, 1), date(2026, 7, 10), "this_month") == (date(2026, 6, 1), date(2026, 6, 10))


def test_this_month_caps_on_shorter_previous_month():
    # 31 июля: в июне 30 дней — cap на конце месяца
    assert resolve_previous_period(date(2026, 7, 1), date(2026, 7, 31), "this_month") == (date(2026, 6, 1), date(2026, 6, 30))


def test_last_month_is_previous_calendar_month_whole():
    # Июнь (30 дн) против мая целиком (31 дн) — без нормировки
    assert resolve_previous_period(date(2026, 6, 1), date(2026, 6, 30), "last_month") == (date(2026, 5, 1), date(2026, 5, 31))


def test_custom_range_is_same_length_adjacent():
    assert resolve_previous_period(date(2026, 7, 5), date(2026, 7, 9), None) == (date(2026, 6, 30), date(2026, 7, 4))
