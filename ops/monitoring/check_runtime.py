"""Read-only post-cutover role/ledger monitor; aggregate data only."""
import argparse
import json
import subprocess
from pathlib import Path
import time

EXPECTED_SCHEMA='f68b92a3b4c5'
WORKERS=('sync-manual','sync-nightly','reports','maintenance','scheduler')
QUERY="""BEGIN READ ONLY; SET LOCAL statement_timeout='3s';
SELECT json_build_object(
 'schema',(SELECT version_num FROM alembic_version LIMIT 1),
 'scheduler_age',COALESCE((SELECT extract(epoch FROM now()-last_tick) FROM background_schedule_cursor WHERE name='calendar-v1'),999999),
 'uncertain',(SELECT count(*) FROM background_jobs WHERE state='uncertain'),
 'expired_leases',(SELECT count(*) FROM background_jobs WHERE state='running' AND (lease_until IS NULL OR lease_until<now()-interval '60 seconds')),
 'manual_wait',COALESCE((SELECT max(extract(epoch FROM now()-available_at)) FROM background_jobs WHERE state='queued' AND queue='sync.manual' AND available_at<now()),0),
 'outbox_wait',COALESCE((SELECT max(extract(epoch FROM now()-o.next_publish_at)) FROM background_outbox o JOIN background_jobs j ON j.id=o.job_id WHERE j.state='queued' AND o.next_publish_at<now()),0),
 'report_unknown',(SELECT count(*) FROM report_route_attempts WHERE state='uncertain'),
 'ai_unknown',(SELECT count(*) FROM assistant_request_runs WHERE state='uncertain'));
COMMIT;"""

def ledger_checks(data):
    return {'schema':data['schema']==EXPECTED_SCHEMA,'scheduler_tick':data['scheduler_age']<180,
      'leases':data['expired_leases']==0,'jobs_known':data['uncertain']==0,
      'report_outcomes_known':data['report_unknown']==0,'ai_outcomes_known':data['ai_unknown']==0,
      'outbox_progress':data['outbox_wait']<180}

def role_checks(containers):
    result={}
    for name,row in containers.items():
        env=dict(v.split('=',1) for v in row['Config']['Env'])
        expected='scheduler' if name=='scheduler' else 'worker'
        result[name]=(row['State']['Running'] and not row['State'].get('OOMKilled',False)
          and env.get('APP_PROCESS_ROLE')==expected and env.get('APP_RELEASE')=='2ce9513'
          and env.get('EXPECTED_SCHEMA_REVISION')==EXPECTED_SCHEMA)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=('ingress','workers'))
    args=parser.parse_args()
    checks={};metrics={}
    try:
        if args.role=='ingress':
            raw=subprocess.check_output(['docker','exec','admirra-db-1','psql','-qAt','-U','postgres','-d','saas_project','-c',QUERY],stderr=subprocess.PIPE,timeout=10)
            data=json.loads(raw)
            checks=ledger_checks(data)
            metrics={k:v for k,v in data.items() if k!='schema'}
        else:
            raw=subprocess.check_output(['docker','inspect',*[f'admirra-workers-{s}-1' for s in WORKERS]],stderr=subprocess.PIPE,timeout=10)
            containers=dict(zip(WORKERS,json.loads(raw)))
            checks=role_checks(containers)
            metrics={s+'_restarts':row['RestartCount'] for s,row in containers.items()}
    except Exception as exc:
        checks={'probe':False}
        print(json.dumps({'probe_error':type(exc).__name__}))
    healthy=all(checks.values())
    lines=[f'admirra_runtime_monitor_ok{{role="{args.role}"}} {int(healthy)}',
           f'admirra_runtime_monitor_timestamp_seconds{{role="{args.role}"}} {int(time.time())}']
    lines += [f'admirra_runtime_check_ok{{role="{args.role}",check="{k}"}} {int(v)}' for k,v in checks.items()]
    lines += [f'admirra_runtime_value{{role="{args.role}",name="{k}"}} {v}' for k,v in metrics.items()]
    target=Path('/var/lib/admirra-api2-monitor')/('runtime-'+args.role+'.prom')
    temp=target.with_suffix('.tmp')
    temp.write_text('\n'.join(lines)+'\n');temp.chmod(0o644);temp.replace(target)
    print(json.dumps({'role':args.role,'healthy':healthy,'checks':checks,'metrics':metrics}))
    raise SystemExit(0 if healthy else 2)

if __name__=='__main__': main()
