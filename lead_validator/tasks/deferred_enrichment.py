"""
Отложенное обогащение лидов (фоновая очередь).

Зарезервировано под будущую интеграцию: Celery/RQ/отдельный worker, чтобы не блокировать
ответ webhook при долгих вызовах внешних API и повторно выгружать CRM после догрузки данных.

Текущая реализация: синхронный пайплайн в `LeadValidator._accept`. Для перехода на очередь:

1. Сохранять лид с минимальным набором полей и сразу отвечать 200.
2. Поставить задачу `run_lead_enrichment(lead_id)` с повторным вызовом social_checker / скоринга.
3. После обновления записи — второй POST на `crm_webhook_url` с тем же `lead_id` и флагом `enrichment_complete`.

Пример заглушки (не вызывается из прод-кода по умолчанию):

    async def enqueue_lead_enrichment(lead_id: UUID) -> None:
        logger.info("Deferred enrichment not configured; lead_id=%s", lead_id)
"""

import logging
from typing import TYPE_CHECKING
from uuid import UUID

logger = logging.getLogger("lead_validator.deferred_enrichment")

if TYPE_CHECKING:
    pass


async def enqueue_lead_enrichment(lead_id: UUID) -> None:
    """Заглушка: при подключении очереди заменить на постановку реальной задачи."""
    logger.debug("enqueue_lead_enrichment: noop for lead_id=%s (configure worker to enable)", lead_id)
