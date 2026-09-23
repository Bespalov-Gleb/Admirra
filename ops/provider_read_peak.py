"""Bounded live-provider IO smoke, explicitly NOT a producer/queue cutover.

Read-only production DB; approved owner and exactly two supplied integrations.
Ads APIs may ONLY read. No OAuth exchange, ads changes, report delivery or bank
request. One small OpenRouter comment and an in-memory PDF render run alongside
two snapshot collections. Results contain aggregates only, never raw responses.
"""
import argparse
import asyncio
from collections import Counter
from datetime import date, timedelta
import json
import logging
import os
import threading
import time
import uuid

import httpx
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


class ReadBudget:
    def __init__(self):
        self.calls = Counter()
        self.lock = threading.Lock()

    def admit(self, request):
        host, path, method = request.url.host, request.url.path, request.method
        accepted = False
        if host == 'ads.vk.com':
            accepted = method == 'GET' and path.startswith(('/api/v2/', '/api/v3/'))
        elif host == 'api-metrica.yandex.net':
            accepted = method == 'GET' and path.startswith(('/stat/v1/', '/management/v1/'))
        elif host == 'api.direct.yandex.com' and method == 'POST':
            body = json.loads(request.content)
            accepted = (path == '/json/v5/reports' and set(body) == {'params'} or
                path in ('/json/v5/campaigns', '/json/v501/campaigns', '/json/v5/clients')
                and str(body.get('method', '')).lower() == 'get')
        elif host == 'api.direct.yandex.ru' and path == '/live/v4/json/' and method == 'POST':
            body = json.loads(request.content)
            accepted = body.get('method') == 'AccountManagement' and body.get('param', {}).get('Action') == 'Get'
        elif host == '10.78.0.3' and request.url.port == 8080 and path == '/api/v1/chat/completions' and method == 'POST':
            body = json.loads(request.content)
            accepted = (type(body.get('max_tokens')) is int and 1 <= body['max_tokens'] <= 384
                and len(json.dumps(body.get('messages'))) <= 3000 and not body.get('tools'))
        if not accepted:
            raise RuntimeError('Read-only peak blocked an unapproved provider operation')
        with self.lock:
            if sum(self.calls.values()) >= 40 or host == '10.78.0.3' and self.calls[host]:
                raise RuntimeError('Provider request budget exhausted')
            self.calls[host] += 1


def factory():
    if os.getenv('WW_TEST') != '1' or os.getenv('WW_TEST_ID') != 'provider-read-peak':
        raise RuntimeError('Explicit scoped smoke required')
    # Server-enforced read-only on every connection, not just a coding convention.
    engine = sa.create_engine(os.environ['DATABASE_URL'], pool_size=1, max_overflow=0,
        connect_args={'options': '-cdefault_transaction_read_only=on -cstatement_timeout=10000 -clock_timeout=3000'})
    return sessionmaker(bind=engine), engine


def owned(db, email):
    from core import models
    owner = db.scalar(sa.select(models.User.id).where(sa.func.lower(models.User.email) == email.lower(),
        models.User.is_active.is_(True), models.User.email_verified.is_(True)))
    if owner is None:
        raise RuntimeError('Approved active owner not found')
    return owner


def inventory(db, owner):
    from core import models
    return [dict(integration=str(i), project=str(c), platform=p.value, campaigns=n)
        for i, c, p, n in db.execute(sa.select(models.Integration.id, models.Client.id,
            models.Integration.platform, sa.func.count(models.Campaign.id))
            .join(models.Client, models.Client.id == models.Integration.client_id)
            .outerjoin(models.Campaign, models.Campaign.integration_id == models.Integration.id)
            .where(models.Client.owner_id == owner, models.Integration.sync_status == models.IntegrationSyncStatus.SUCCESS,
                models.Integration.platform.in_([models.IntegrationPlatform.YANDEX_DIRECT, models.IntegrationPlatform.VK_ADS]))
            .group_by(models.Integration.id, models.Client.id)
            .having(sa.func.count(models.Campaign.id).between(1, 20))
            .order_by(sa.func.count(models.Campaign.id), models.Integration.id).limit(20))]


async def run(plans, engine, *, ads_only=False):
    from automation import ads_sync_work as ads
    from ai.comment_llm import create_comment
    from backend_api.reports.pdf_service import generate_report_pdf_from_snapshot
    budget = ReadBudget()
    responses = []
    original = httpx.AsyncClient._send_single_request
    async def guarded(client, request):
        budget.admit(request)
        assert engine.pool.checkedout() == 0, 'SQL remained held during provider IO'
        response = await original(client, request)
        await response.aread()
        entry = {'host': request.url.host, 'path': request.url.path, 'status': response.status_code}
        if request.url.host == 'api.direct.yandex.com' and request.url.path.endswith('/reports') and response.status_code == 200:
            lines = response.text.splitlines()
            entry['tsv_shape'] = {'lines': len(lines), 'widths': [len(line.split('\t')) for line in lines[:5]],
                'has_column_header': any(line.startswith('Date\t') for line in lines),
                'has_totals': any(line.startswith('Total rows:') for line in lines),
                'quoted_report_name': bool(lines and lines[0].startswith('"AgencyStats_'))}
            fields = next((line.split('\t') for line in lines if line.startswith('Date\t')), [])
            entry['tsv_shape']['missing_identifiers'] = {
                field: sum(1 for line in lines if len(line.split('\t')) == len(fields)
                    and line.split('\t')[0] != 'Date' and line.split('\t')[index] == '--')
                for index, field in enumerate(fields) if field.endswith('Id')}
            if 'AdGroupName' in fields:
                rows = [line.split('\t') for line in lines if len(line.split('\t')) == len(fields) and not line.startswith('Date\t')]
                entry['tsv_shape']['group_name_missing'] = sum(row[fields.index('AdGroupName')] == '--' for row in rows)
                entry['tsv_shape']['distinct_group_keys'] = len({(row[0], row[1], row[3], row[4]) for row in rows})
        if response.is_error:
            try:
                error = response.json().get('error', {})
                code = error.get('error_code', error.get('code')) if isinstance(error, dict) else None
                if isinstance(code, int) or isinstance(code, str) and code.replace('_', '').isalnum() and len(code) < 50:
                    entry['code'] = code
            except (ValueError, AttributeError):
                pass
        responses.append(entry)
        return response
    httpx.AsyncClient._send_single_request = guarded
    started = time.monotonic()
    async def collect(plan):
        snapshot = await ads.collect(plan)  # validate, but NEVER apply to production.
        return {'platform': plan.platform.value, 'catalog': len(snapshot['catalog']),
            'rows': {k: len(v) for k, v in snapshot['data'].items()}, 'goals': len(snapshot['goals'])}
    async def comment():
        result = await create_comment(system='Короткая техническая проверка. Ответь только: Проверка успешна.',
            messages=[{'role': 'user', 'content': 'Подтверди доступность сервиса.'}], max_tokens=384)
        if not result.content[0].text:
            raise RuntimeError('Empty model result')
        return {'model': result.model, 'cost_usd': str(result.cost_usd),
            'input_tokens': result.usage.input_tokens, 'output_tokens': result.usage.output_tokens}
    async def report():
        # In-memory render of a synthetic fixed snapshot; no public file/recipient.
        snapshot = {'client_name': 'Synthetic acceptance', 'start_date': plans[0].start,
            'end_date': plans[0].end, 'summary': {'expenses': 1000, 'leads': 5,
                'clicks': 100, 'impressions': 1000, 'cpc': 10, 'cpa': 200},
            'top_campaigns': [], 'platform': 'vk'}
        pdf = await asyncio.to_thread(generate_report_pdf_from_snapshot, snapshot, '')
        if not pdf.startswith(b'%PDF'):
            raise RuntimeError('Invalid rendered PDF')
        return {'pdf_bytes': len(pdf)}
    try:
        calls = [collect(plan) for plan in plans]
        if not ads_only:
            calls.extend([comment(), report()])
        results = await asyncio.wait_for(asyncio.gather(*calls, return_exceptions=True), 120)
        failures = [isinstance(value, BaseException) for value in results]
        from automation.ads_sync_contract import IncompleteAdsSnapshot
        safe = [{'error_type': type(value).__name__,
            'contract_error': str(value) if type(value) is IncompleteAdsSnapshot else None,
            'http_status': getattr(getattr(value, 'response', None), 'status_code', None)}
            if failed else value for value, failed in zip(results, failures)]
        return {'status': 'blocked' if any(failures) else 'passed', 'seconds': round(time.monotonic() - started, 3),
            'provider_requests': dict(budget.calls), 'responses': responses, 'results': safe,
            'production_db_writes': 0, 'customer_sends': 0, 'bank_calls': 0}
    finally:
        httpx.AsyncClient._send_single_request = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email', required=True)
    parser.add_argument('--integration', action='append', default=[], type=uuid.UUID)
    parser.add_argument('--ads-only', action='store_true', help='Do not repeat the paid AI/render smoke during ads diagnostics')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)  # Third-party legacy logs may contain response bodies.
    session, engine = factory()
    try:
        with session() as db:
            owner = owned(db, args.email)
            if not args.integration:
                print(json.dumps({'mode': 'read-only inventory', 'integrations': inventory(db, owner)}))
                return
            if len(set(args.integration)) != 2:
                raise RuntimeError('Exactly two distinct approved integration IDs required')
            allowed = {row['integration'] for row in inventory(db, owner)}
            if not set(map(str, args.integration)) <= allowed:
                raise RuntimeError('Scope escaped approved owner/size/status')
            from automation.ads_sync_work import prepare
            day = (date.today() - timedelta(days=1)).isoformat()
            plans = [prepare(db, identifier, day, day) for identifier in args.integration]
        result = asyncio.run(run(plans, engine, ads_only=args.ads_only))
        print(json.dumps(result))
        if result['status'] != 'passed':
            raise SystemExit(1)
    except Exception as error:
        print(json.dumps({'status': 'blocked', 'error_type': type(error).__name__}))
        raise SystemExit(1) from None
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
