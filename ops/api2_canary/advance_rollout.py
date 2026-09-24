"""Explicit 25%/50% launch steps; retain rollback bytes and enforce soak time.

Run on ingress as root only after cross-replica mutation/file acceptance. Never
automatically retries mutations, restarts services or changes application env.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import urllib.request

from ops.cutover_admission.manage import transact
from ops.render_launch_runtime import private_json
from ops.api2_canary.check_canary import recent_canary_rows


def weighted(source, stage):
    if stage not in (25, 50):
        raise ValueError('Unsupported rollout step')
    for address, weight in [('127.0.0.1', 3 if stage == 25 else 1), ('10.77.0.2', 1)]:
        pattern=rf'(server {re.escape(address)}:8001 weight=)\d+( max_fails=(?:1|3) fail_timeout=(?:10|5)s;)'
        source,count=re.subn(pattern,lambda m: m[1]+str(weight)+m[2],source)
        if count!=1:
            raise ValueError('Upstream configuration drift')
    return source


def business_routes(source):
    # Existing exact safe-read routes retain their bounded retry policy. Only
    # the generic API and attachment/SSE prefix join the full traffic pool.
    patterns=[r'(location /api/ \{)([^{}]*)(\})',
              r'(location ~ \^/api/assistant/conversations/ \{)([^{}]*)(\})']
    changed=0
    def replace(match):
        nonlocal changed
        body=match[2]
        old=r'proxy_pass http://127\.0\.0\.1:8001(?:/api/)?;'
        if len(re.findall(old,body))!=1:
            raise ValueError('API route drift or already expanded')
        body=re.sub(old,'proxy_pass http://admirra_api_read_canary;',body)
        if 'proxy_next_upstream' in body:
            raise ValueError('Unexpected preexisting retry policy')
        body+='        proxy_next_upstream off;\n        proxy_connect_timeout 1s;\n'
        body+='        proxy_set_header Connection "";\n        proxy_set_header X-Request-ID $request_id;\n'
        body+='        access_log /var/log/nginx/admirra-api2-canary.log admirra_api_canary;\n'
        if 'proxy_read_timeout' not in body:
            body+='        proxy_read_timeout 120s;\n'
        if 'proxy_send_timeout' not in body:
            body+='        proxy_send_timeout 120s;\n'
        body+='    '
        changed+=1
        return match[1]+body+match[3]
    for pattern in patterns:
        source=re.sub(pattern,replace,source)
    if changed not in (1,2):
        raise ValueError('Expected the existing API routes')
    return source


def soak_ready(previous, now):
    start=dt.datetime.fromisoformat(previous['started_at'])
    return start.tzinfo is not None and (now-start).total_seconds()>=1800


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=int,choices=(25,50),required=True)
    parser.add_argument('--release-root',type=Path,required=True)
    parser.add_argument('--accepted-cross-replica-checks',action='store_true',required=True)
    args=parser.parse_args()
    root=args.release_root
    if root.stat().st_uid!=0 or root.stat().st_mode & 0o077:
        raise ValueError('Protected release directory required')
    now=dt.datetime.now(dt.timezone.utc)
    previous=json.loads((root/('canary-10-start.json' if args.stage==25 else 'canary-25-start.json')).read_text())
    if not soak_ready(previous,now):
        raise ValueError('Minimum thirty minute previous-stage observation not complete')
    start=dt.datetime.fromisoformat(previous['started_at'])
    readings=[]
    for line in (root/'public-read-watch.log').read_text().splitlines():
        if not line.startswith('{'): continue
        entry=json.loads(line)
        if 'at' not in entry: raise ValueError('Synthetic smoke failed')
        if dt.datetime.fromisoformat(entry['at'])>=start:
            readings.append(entry)
    if len(readings)<20 or dt.datetime.fromisoformat(readings[-1]['at'])<now-dt.timedelta(minutes=2):
        raise ValueError('Insufficient fresh controlled traffic evidence')
    if any(set(r['statuses'])!={'200'} or r['p95_ms']>=5000 for r in readings):
        raise ValueError('Read error or latency gate failed')
    for base in ('http://127.0.0.1:8001','http://10.77.0.2:8001'):
        data=json.load(urllib.request.urlopen(base+'/api/health/ready',timeout=5))
        if data!={'status':'ok','role':'api','release':'2ce9513'}:
            raise ValueError('Runtime/schema readiness drift')
    alerts=json.load(urllib.request.urlopen('http://127.0.0.1:9090/api/v1/alerts',timeout=5))
    if any(a['state']=='firing' for a in alerts['data']['alerts']):
        raise ValueError('Active monitoring alert blocks expansion')
    rows=list(recent_canary_rows(Path('/var/log/nginx/admirra-api2-canary.log'),1800))
    if any(row.get('status','').startswith('5') for row in rows):
        raise ValueError('Public final 5xx blocks expansion')
    count=sum(row.get('upstream','').startswith('10.77.0.2:8001') for row in rows)
    if count<10: raise ValueError('API2 has not served enough real requests')
    query="SELECT count(*) FROM background_jobs WHERE state='uncertain' OR (state='running' AND lease_until<now())"
    # Actual column contract is checked in the reviewed schema; no credentials.
    unhealthy=subprocess.check_output(['docker','exec','admirra-db-1','psql','-U','postgres','-d','saas_project','-Atc',query],text=True).strip()
    if unhealthy!='0': raise ValueError('Jobs require reconciliation')
    path=Path('/etc/nginx/conf.d/admirra-api2-upstream.conf')
    writes={path:(weighted(path.read_text(),args.stage).encode(),0o644)}
    if args.stage==25:
        for name in ('admirra.ru','admirra.online'):
            site=Path('/etc/nginx/sites-enabled')/name
            writes[site.resolve()]=(business_routes(site.read_text()).encode(),0o644)
    saved={str(p.resolve()):p.read_text() for p in writes}
    private_json(root/f'canary-{args.stage}-previous-nginx.json',saved)
    transact(writes)
    evidence={'started_at':dt.datetime.now(dt.timezone.utc).isoformat(),'api2_weight':1,
        'api1_weight':3 if args.stage==25 else 1,'scope':'all-business-api-routes',
        'previous_stage_requests':len(rows),'previous_stage_api2':count,'synthetic_batches':len(readings)}
    private_json(root/f'canary-{args.stage}-start.json',evidence)
    print(json.dumps(evidence))


if __name__=='__main__':
    main()
