"""Классификация ошибок синхронизации для повторов.

До этого условие повтора выглядело как ``"5" in str(e).lower()`` — под него
попадала любая ошибка, где встречается цифра 5 (UUID, дата, идентификатор
кампании). Мёртвая интеграция с 401/404 повторяла полный обход внешнего API
три раза подряд. Тесты фиксируют реальные тексты ошибок с прода.
"""
import asyncio

import pytest

from backend_api.sync_jobs import SyncJobTimeout, _is_retriable_error


# Реальные тексты из sync_jobs.error на проде — повторять их бессмысленно.
FATAL_PROD_ERRORS = [
    "Bad request to Yandex API: Yandex Direct API Error: 400 - Ошибка авторизации | detail: ...",
    "Yandex Direct API Error: 404 - Объект не найден | detail: В HTTP-заголовке Client-Login ...",
    "У интеграции отсутствует токен доступа",
    "Bad request to Yandex API: Yandex Direct API Error: 400 - Ваш логин не подключен к агентству",
    'Failed to fetch goals for counter facebook.tim: 400 - {"errors":[{"error_type":"invalid_parameter"}]}',
]

RETRIABLE_ERRORS = [
    "429 Too Many Requests",
    "HTTP 503 Service Unavailable",
    "VK Ads API error: status=502",
    "Read timeout while fetching report",
    "Connection reset by peer",
    "Превышен лимит запросов, повторите попытку позже",
]


@pytest.mark.parametrize("message", FATAL_PROD_ERRORS)
def test_fatal_errors_are_not_retried(message):
    assert _is_retriable_error(Exception(message)) is False


@pytest.mark.parametrize("message", RETRIABLE_ERRORS)
def test_transient_errors_are_retried(message):
    assert _is_retriable_error(Exception(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        # Раньше каждая из этих строк считалась повторяемой из-за подстроки "5".
        "Sync failed for integration 0d45ceae-78dd-4f75-b42d-654c8b4d5669",
        "Campaign 15837462 not found in catalog",
        "Unexpected payload for 2026-07-25",
        # Статус-код внутри hex-UUID не должен считаться статусом.
        "integration a500b1c2-3d4e-5f6a-7b8c-9d0e1f2a3b4c is broken",
    ],
)
def test_digit_five_alone_is_not_a_retry_signal(message):
    assert _is_retriable_error(Exception(message)) is False


def test_job_timeout_is_never_retried():
    """Задача, снятая по таймауту, не должна повторяться ещё дважды."""
    assert _is_retriable_error(SyncJobTimeout("превышен лимит 900 с")) is False


def test_network_exceptions_are_retried():
    assert _is_retriable_error(asyncio.TimeoutError()) is True
    assert _is_retriable_error(ConnectionError("connection refused")) is True


def test_httpx_status_errors_use_status_code():
    httpx = pytest.importorskip("httpx")

    request = httpx.Request("GET", "https://api.direct.yandex.com/")

    retriable = httpx.HTTPStatusError(
        "server error", request=request, response=httpx.Response(503, request=request)
    )
    fatal = httpx.HTTPStatusError(
        "forbidden", request=request, response=httpx.Response(403, request=request)
    )

    assert _is_retriable_error(retriable) is True
    assert _is_retriable_error(fatal) is False
