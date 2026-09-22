"""Enable one eligible test account, only after live Check configuration is ready.

Run alongside release.py on API1. Never changes user history, trial or payments.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import uuid

from release import compose, env, inspect, literal, private_json, ready, run, start, AUDIT

parser=argparse.ArgumentParser()
parser.add_argument('--email',required=True)
parser.add_argument('--preflight-only',action='store_true')
args=parser.parse_args()

probe='''
import base64, hashlib, hmac, json, urllib.request
import httpx, sqlalchemy as sa
from core.database import SessionLocal
from core.config import get_config
from core import models
from backend_api.services import signup_discount as discount
cfg=get_config().cloudpayments
response=httpx.post('https://api.cloudpayments.ru/site/notifications/check/get',
    auth=(cfg.public_id,cfg.api_secret),json={},timeout=15)
response.raise_for_status()
body=response.json()
assert body.get('Success') is True
check=body['Model']
check_ready=(check.get('IsEnabled') is True
    and check.get('Address')=='https://admirra.ru/api/billing/cloudpayments/check'
    and check.get('HttpMethod')=='POST')
raw=b'{"AccountId":"signup-preflight-not-a-user"}'
signature=base64.b64encode(hmac.new(cfg.api_secret.encode(),raw,hashlib.sha256).digest()).decode()
request=urllib.request.Request('https://admirra.ru/api/billing/cloudpayments/check',data=raw,
    headers={'Content-Type':'application/json','Content-HMAC':signature})
with urllib.request.urlopen(request,timeout=15) as r:
    assert json.load(r)=={'code':11}
with SessionLocal() as db:
    db.execute(sa.text('SET TRANSACTION READ ONLY'))
    user=db.query(models.User).filter(models.User.email==EMAIL).one()
    sub=db.query(models.Subscription).filter_by(user_id=user.id).order_by(models.Subscription.created_at.desc()).first()
    assert discount.eligible_trial(db,user,sub)
    print(json.dumps({'user_id':str(user.id),'eligible':True,'check_ready':check_ready,'signed_check':True}))
'''.replace('EMAIL',repr(args.email))

with open('/var/lock/admirra-summary-release.lock','w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    raw=run(['docker','exec','-i','admirra-backend-1','python','-'],input=probe)
    result=json.loads(next(line for line in raw.splitlines() if line.startswith('{')))
    uid=str(uuid.UUID(result['user_id']))
    print('Eligible account; signed Check passed; Check enabled:',result['check_ready'],flush=True)
    if args.preflight_only:
        raise SystemExit(0)
    assert result['check_ready'], 'Check must be configured before enabling any discount'
    audit_raw=run(['docker','exec','-i','admirra-backend-1','python','-'],input=AUDIT)
    audit=json.loads(next(line for line in audit_raw.splitlines() if line.startswith('{')))
    assert not any(v for k,v in audit.items() if k!='schema'), 'Retry in a quiet window'
    old={service:inspect(service) for service in ('backend','automation')}
    directory=Path('/etc/admirra/releases')/('signup-pilot-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(mode=0o700)
    wanted={}
    for service,row in old.items():
        assert row['Config']['Labels'].get('ru.admirra.signup-discount.revision')=='signup-20260922'
        previous=env(row)
        assert previous['SIGNUP_DISCOUNT_ENABLED']=='false' and not previous['SIGNUP_DISCOUNT_PILOT_USER_IDS']
        path=row['Config']['Labels']['com.docker.compose.project.config_files']
        config=json.loads(run(compose(path)+['config','--format','json']))
        config['services'][service]['environment']=previous
        config['services'][service]['image']=row['Image']
        config['services'][service].pop('build',None)
        config['services'][service].pop('env_file',None)
        private_json(directory/(service+'-previous.json'),literal(config))
        active=deepcopy(config)
        active['services'][service]['environment']['SIGNUP_DISCOUNT_PILOT_USER_IDS']=uid
        wanted[service]=active['services'][service]['environment']
        private_json(directory/(service+'-active.json'),literal(active))
    private_json(directory/'metadata.json',{'active':{s:row['Image'] for s,row in old.items()},'pilot_user_id':uid})
    try:
        for service in old:
            start(directory/(service+'-active.json'),service)
            if service=='backend': ready()
            row=inspect(service)
            assert row['Image']==old[service]['Image'] and env(row)==wanted[service]
            assert row['State']['Running'] and row['RestartCount']==0
    except BaseException:
        for service in old:
            start(directory/(service+'-previous.json'),service)
        raise
    print('Pilot enabled for exactly one account; other accounts stay disabled. Config:',directory,flush=True)
