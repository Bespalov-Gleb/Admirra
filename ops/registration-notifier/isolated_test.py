"""Run on a Docker host; creates only a temporary internal network/database."""
import os
from pathlib import Path
import subprocess
import time
import uuid


def run(*args, **kwargs):
    return subprocess.run(args,check=True,text=True,**kwargs)


root=Path(__file__).resolve().parent
name='admirra-registration-qa-'+uuid.uuid4().hex[:8]
image=os.environ['NOTIFIER_IMAGE']
pgimage=run('docker','image','inspect','postgres:15-alpine','--format','{{.Id}}',capture_output=True).stdout.strip()
run('docker','network','create','--internal',name,capture_output=True)
try:
    run('docker','run','-d','--name',name,'--network',name,'--network-alias','testdb',
        '--memory','128m','--cpus','0.5','--tmpfs','/var/lib/postgresql/data:rw,size=128m',
        '-e','POSTGRES_PASSWORD=isolated-test-only','-e','POSTGRES_DB=notifier_test',pgimage,capture_output=True)
    for _ in range(30):
        result=subprocess.run(['docker','exec',name,'pg_isready','-U','postgres'],capture_output=True)
        if result.returncode==0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Isolated database did not start')
    run('docker','run','--rm','--network',name,'--memory','192m','--cpus','0.5',
        '--read-only','--tmpfs','/tmp:rw,size=16m','--cap-drop','ALL',
        '-e','WW_TEST=1','-e','WW_TEST_ID='+name,
        '-e','NOTIFIER_TEST_DSN=postgresql://postgres:isolated-test-only@testdb/notifier_test',
        '-v',str(root)+':/qa:ro','--entrypoint','python',image,'-B','/qa/test_notifier.py')
finally:
    subprocess.run(['docker','rm','-f','-v',name],capture_output=True)
    subprocess.run(['docker','network','rm',name],capture_output=True)
