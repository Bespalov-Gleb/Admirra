"""Targeted host-only release. Price snapshots preserved; no payment API calls.

--audit is read-only. --activate REV takes already built billing-REV images.
Root-only backups retain exact old environments, .env and subscription snapshots.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path('/root/Admirra')
BACKUPS = Path('/root/admirra-billing-backups')
HERE = Path(__file__).resolve().parent
SERVICES = ('backend', 'automation', 'frontend')
EXPECTED = {
    'backend':'sha256:6bd6367835a6dd9cdab99e01cf3756c69d1c92034845517b2f355076ef8bcc63',
    'frontend':'sha256:564e5373a9adbaf5ab6fd9941aae5f3070d874c5476238822dd343c8f1f0f1d1',
    'automation':'sha256:33b4ca03408c55cd11093fa3c4f9b86ecf1f323f50636222a43ea71bb4217ab8',
}
PRICES = {
    'BILLING_PLAN_START_PRICE_RUB':'2900', 'BILLING_PLAN_BASIC_PRICE_RUB':'6900',
    'BILLING_PLAN_STANDARD_PRICE_RUB':'13900', 'BILLING_SLOT_PRICE_START_RUB':'1100',
    'BILLING_SLOT_PRICE_AGENCY_RUB':'800', 'BILLING_SLOT_PRICE_PRO_RUB':'650',
}
MATRIX = {'start':[2900,29000,1100], 'agency':[6900,69000,800], 'pro':[13900,139000,650]}

def capture(args, **kw):
    return subprocess.check_output(args, cwd=ROOT, text=True, **kw)

def inspect():
    return {s:json.loads(capture(['docker','inspect','admirra-'+s+'-1']))[0] for s in SERVICES}

def env(row):
    return dict(v.split('=',1) for v in row['Config']['Env'])

def write(path, obj):
    with os.fdopen(os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600),'w') as f:
        json.dump(obj,f)

def literal(value):
    if isinstance(value,str): return value.replace('$','$$')
    if isinstance(value,dict): return {k:literal(v) for k,v in value.items()}
    if isinstance(value,list): return [literal(v) for v in value]
    return value

def compose(path):
    return ['docker','compose','-p','admirra','--project-directory',str(ROOT),'-f',str(path)]

def start(path, service):
    subprocess.run(compose(path)+['up','-d','--no-deps','--no-build','--pull','never','--timeout','60',service],
                   cwd=ROOT,check=True)

def healthy():
    for _ in range(30):
        r=subprocess.run(['docker','exec','admirra-backend-1','python','-c',
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/openapi.json',timeout=3)"],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if r.returncode == 0: return
        time.sleep(2)
    raise RuntimeError('Backend health check failed')

def audit(freeze=False):
    code=(HERE/'price_snapshots.py').read_text()
    raw=capture(['docker','exec','-i','admirra-backend-1','python','-',*(['--freeze'] if freeze else [])],input=code)
    line=next(x for x in raw.splitlines() if x.startswith('BILLING_AUDIT_JSON='))
    return json.loads(line.partition('=')[2])

def updated_prices(oldenv):
    raw=json.loads(oldenv.get('BILLING_PRICE_BOOK_JSON') or '{}')
    book=deepcopy(raw if 'plans' in raw else {'plans':{k:v for k,v in raw.items() if k != 'version'}})
    book['version']=max(2,int(raw.get('version',1))+1)
    for code,(month,year,slot) in MATRIX.items():
        book.setdefault('plans',{}).setdefault(code,{}).update(
            price_month=month,price_year=year,extra_project_price_month=slot,
            extra_project_price_year=round(slot*12*.83))
    return {**PRICES,'BILLING_PRICE_BOOK_JSON':json.dumps(book,separators=(',',':'))}

def replace_env(path, values):
    text=path.read_text()
    for key,value in values.items():
        pattern=r'^'+re.escape(key)+r'=.*$'
        line=key+'='+value
        if re.search(pattern,text,re.M): text=re.sub(pattern,lambda _:line,text,flags=re.M)
        else: text=text.rstrip()+'\n'+line+'\n'
    tmp=path.with_name('.env.billing-new')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: f.write(text)
    os.replace(tmp,path)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def activate(revision):
    old=inspect()
    if any(old[s]['Image'] != EXPECTED[s] for s in SERVICES):
        raise RuntimeError('Runtime image drift; review deployment')
    before=audit()
    print('Preflight:',json.dumps(before['summary']),flush=True)
    if before['summary']['running_sync_jobs'] or before['summary']['sending_reports']:
        raise RuntimeError('Active sync or delivery; retry at a quiet moment')
    prices=updated_prices(env(old['backend']))
    if updated_prices(env(old['automation'])) != prices:
        raise RuntimeError('Backend/automation price books differ; manual review required')
    images={s:capture(['docker','image','inspect','--format','{{.Id}}',f'admirra-{s}:billing-{revision}']).strip()
            if s != 'automation' else old[s]['Image'] for s in SERVICES}
    base=json.loads(capture(['docker','compose','config','--format','json']))
    for s in SERVICES:
        service=base['services'][s]
        service.pop('build',None)
        service.pop('env_file',None)
        service['environment']=env(old[s])
        service['image']=old[s]['Image']
    snapshot=BACKUPS/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    snapshot.mkdir(mode=0o700)
    write(snapshot/'original.json',literal(base))
    write(snapshot/'subscriptions-before.json',before)
    with os.fdopen(os.open(snapshot/'env.before',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:
        f.write((ROOT/'.env').read_bytes())
    wanted={}
    for s in SERVICES:
        service=base['services'][s]
        service['image']=images[s]
        if s in ('backend','automation'): service['environment'].update(prices)
        wanted[s]=dict(service['environment'])
    write(snapshot/'active.json',literal(base))
    resolved=json.loads(capture(compose(snapshot/'active.json')+['config','--format','json']))
    if any(resolved['services'][s]['environment'] != wanted[s] for s in SERVICES):
        raise RuntimeError('Environment serialization drift')
    print('Snapshot:',snapshot,flush=True)
    frozen=audit(freeze=True)
    write(snapshot/'subscriptions-frozen.json',frozen)
    print('Snapshots frozen:',frozen['summary']['changed'],flush=True)
    try:
        replace_env(ROOT/'.env',prices)
        start(snapshot/'active.json','backend')
        healthy()
        start(snapshot/'active.json','automation')
        start(snapshot/'active.json','frontend')
        current=inspect()
        for s in SERVICES:
            if env(current[s]) != wanted[s] or current[s]['Image'] != images[s]:
                raise RuntimeError('Runtime image/environment drift: '+s)
        after=audit()
        for code,expected in MATRIX.items():
            if after['summary']['catalog'][code] != expected:
                raise RuntimeError('New catalog mismatch: '+code)
        oldsign={r['id']:r['signature'] for r in frozen['records']}
        if any(oldsign[r['id']] != r['signature'] for r in after['records'] if r['id'] in oldsign):
            raise RuntimeError('Existing subscription effective price changed; investigate')
        write(snapshot/'subscriptions-after.json',after)
        subprocess.run(['curl','-fsS','--retry','6','--retry-delay','2','--retry-all-errors',
                        '-o','/dev/null','https://admirra.ru/'],check=True)
        write(snapshot/'metadata.json',{'revision':revision,'active':images,'previous':EXPECTED,
            'env_sha256':digest(ROOT/'.env'),'nginx_sha256':digest(ROOT/'nginx.conf')})
        print('Activated:',json.dumps(after['summary']),flush=True)
        print('Existing price signatures unchanged:',len(oldsign),flush=True)
    except BaseException:
        print('Activation failed: restoring images and environments.',flush=True)
        (ROOT/'.env').write_bytes((snapshot/'env.before').read_bytes())
        for s in ('backend','automation','frontend'): start(snapshot/'original.json',s)
        healthy()
        raise

def rollback(snapshot):
    meta=json.loads((snapshot/'metadata.json').read_text())
    current=inspect()
    if digest(ROOT/'.env') != meta['env_sha256'] or digest(ROOT/'nginx.conf') != meta['nginx_sha256']:
        raise RuntimeError('Configuration drift; manual rollback review needed')
    if any(current[s]['Image'] != meta['active'][s] for s in SERVICES):
        raise RuntimeError('Image drift; manual rollback review needed')
    # Do not undo DB snapshots: they preserve prices, including purchases since rollout.
    (ROOT/'.env').write_bytes((snapshot/'env.before').read_bytes())
    for s in ('backend','automation','frontend'): start(snapshot/'original.json',s)
    healthy()
    print('Previous images/env restored; subscription snapshots preserved.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--audit',action='store_true')
    group.add_argument('--activate')
    group.add_argument('--rollback',type=Path)
    args=parser.parse_args()
    if args.audit:
        print(json.dumps(audit()['summary']))
    else:
        BACKUPS.mkdir(mode=0o700,exist_ok=True)
        with (BACKUPS/'deploy.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if args.rollback: rollback(args.rollback)
            else: activate(args.activate)
