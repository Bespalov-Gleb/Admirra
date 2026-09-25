"""Isolated synthetic PostgreSQL + bounded test container, no production data."""
import os
from pathlib import Path
import subprocess
import time
import uuid

def run(*args,**kwargs):
    return subprocess.run(args,check=True,text=True,**kwargs)

root=Path(__file__).resolve().parent.parent
image=os.environ['QA_IMAGE']
name='admirra-signup-qa-'+uuid.uuid4().hex[:8]
candidate = os.getenv('QA_CANDIDATE_IMAGE') == '1'
test_image = None
if candidate:
    # Preserve candidate application bytes, but never load inherited .env files
    # in tests. This temporary image isn't deployed or published.
    candidate_id = run('docker','image','inspect',image,'--format','{{.Id}}',capture_output=True).stdout.strip()
    base_tag = name + ':base'
    test_image = name + ':sanitized'
    run('docker','tag',candidate_id,base_tag)
    dockerfile = ('FROM ' + base_tag + '\n'
        'RUN python -c "from pathlib import Path; [p.unlink() for p in Path(\'/app\').glob(\'.env*\') if p.is_file()]"\n')
    run('docker','build','--network=none','--pull=false','-t',test_image,'-',input=dockerfile,capture_output=True)
    image = test_image
pgimage=run('docker','image','inspect','postgres:15-alpine','--format','{{.Id}}',capture_output=True).stdout.strip()
run('docker','network','create','--internal',name,capture_output=True)
try:
    run('docker','run','--pull','never','-d','--name',name,'--network',name,'--network-alias','test-db',
        '--memory','256m','--cpus','0.5','--tmpfs','/var/lib/postgresql/data:rw,size=256m',
        '-e','POSTGRES_PASSWORD=isolated-test-only','-e','POSTGRES_DB=signup_test',pgimage,capture_output=True)
    for _ in range(30):
        if subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True).returncode==0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Isolated database not ready')
    url='postgresql://postgres:isolated-test-only@test-db/signup_test'
    mounts = ['-v',str(root)+':/qa:ro']
    if candidate:
        mounts += ['-v',str(root/'tests')+':/app/tests:ro', '-v',str(root/'ops')+':/app/ops:ro',
                   '-v',str(root/'alembic/versions/ef1a2b3c4d5e_signup_discount.py')+':/app/alembic/versions/ef1a2b3c4d5e_signup_discount.py:ro']
    tests = ['tests/test_signup_discount.py','tests/test_purchase_analytics.py','tests/test_signup_discount_flow.py','tests/test_onboarding.py','tests/test_onboarding_ingress.py',
             'tests/test_billing_slot_purchase.py','tests/test_billing_guards.py']
    if not candidate:
        tests += ['tests/test_billing_work.py','-k','not test_recurring_changed_after_io_blocks_redelivery_and_next_occurrence']
    run('docker','run','--pull','never','--rm','--network',name,'--memory','512m','--cpus','1',
        '--read-only','--tmpfs','/tmp:rw,size=64m','--cap-drop','ALL',
        '-e','WW_TEST=1','-e','WW_TEST_ID='+name,'-e','DATABASE_URL='+url,'-e','ISOLATED_POSTGRES_URL='+url,
        '-e','PYTHONPATH='+('/app' if candidate else '/qa:/app'),*mounts,'-w','/app' if candidate else '/qa','--entrypoint','python',image,
        '-B','ops/run_isolated_tests.py',*tests,'--disable-warnings')
finally:
    subprocess.run(['docker','rm','-f','-v',name],capture_output=True)
    subprocess.run(['docker','network','rm',name],capture_output=True)
    if test_image:
        subprocess.run(['docker','image','rm',test_image,base_tag],capture_output=True)
