"""Read one failed job's Direct catalogue; never log credentials or mutate DB."""
import asyncio
import json
import logging
import sys
import uuid

from sqlalchemy import text
from core.database import SessionLocal
from core import models, security


async def main(job_id):
    logging.disable(logging.CRITICAL)
    with SessionLocal() as db:
        db.execute(text('SET TRANSACTION READ ONLY'))
        job = db.get(models.SyncJob, uuid.UUID(job_id))
        integration = db.get(models.Integration, job.integration_id)
        assert integration.platform == models.IntegrationPlatform.YANDEX_DIRECT
        from automation.sync import _selected_yandex_direct_profile
        token = security.decrypt_token(integration.access_token)
        profile = _selected_yandex_direct_profile(integration)
    from automation.yandex_direct import YandexDirectAPI
    from automation.provider_transport import provider_client
    api = YandexDirectAPI(token, client_login=profile)
    async with provider_client('direct') as client:
        response = await client.post(api.campaigns_url, headers=api.headers, timeout=30,
            json={'method': 'get', 'params': {'SelectionCriteria': {
                'States': ['ON', 'OFF', 'SUSPENDED', 'ENDED', 'CONVERTED', 'ARCHIVED']},
                'FieldNames': ['Id', 'Name', 'Status', 'State', 'StatusPayment', 'Type'],
                'Page': {'Limit': 1000, 'Offset': 0}}})
    payload = response.json()
    error = payload.get('error') or {}
    print(json.dumps({'http': response.status_code, 'error_code': error.get('error_code'),
        'error_string': error.get('error_string'), 'error_detail': error.get('error_detail'),
        'count': len((payload.get('result') or {}).get('Campaigns', [])),
        'limited_by': (payload.get('result') or {}).get('LimitedBy')}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
