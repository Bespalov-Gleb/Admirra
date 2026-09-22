"""Scoped initial installation on API-1. Does not restart app services.

Token is entered without echo. No real user/contact data is printed.
Run only after isolated_test.py passed. Existing installation is never replaced.
"""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def private_file(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o440)
    try:
        os.fchown(fd, 0, 65534)
        with os.fdopen(fd, 'w') as out:
            out.write(data)
    except BaseException:
        # Never print content on installation failure.
        raise


parser = argparse.ArgumentParser()
parser.add_argument('--chat-id', type=int, required=True)
parser.add_argument('--bot-id', required=True)
parser.add_argument('--image', required=True)
args = parser.parse_args()
assert args.chat_id < 0 and re.fullmatch(r'sha256:[a-f0-9]{64}', args.image)
root = Path(__file__).resolve().parent
secret_dir = Path('/etc/admirra/registration-notifier')
if secret_dir.exists():
    raise SystemExit('Existing secret directory preserved; review installation state before continuing')
token = getpass.getpass('New registration bot token (hidden): ').strip()
if not re.fullmatch(re.escape(args.bot_id) + r':[A-Za-z0-9_-]+', token):
    raise SystemExit('Unexpected bot ID/token format')
password = secrets.token_hex(32)
secret_dir.mkdir(mode=0o750, parents=True)
os.chown(secret_dir, 0, 65534)
private_file(secret_dir/'bot-token',token+'\n')
private_file(secret_dir/'database-url',f'postgresql://admirra_registration_notifier:{password}@db:5432/saas_project\n')
private_file(secret_dir/'config.json',json.dumps({
    'chat_id':args.chat_id,'api_base':'http://10.78.0.3:8080/telegram',
    'token_file':'/run/secrets/bot-token','database_file':'/run/secrets/database-url',
    'synthetic_domain':'vk-oauth.admirra.ru',
})+'\n')
# Snapshot only schema, not account contents. Rollback disables just this trigger.
schema = command(['docker','exec','admirra-db-1','pg_dump','-U','postgres','-d','saas_project',
    '--schema-only','--no-owner','--no-acl','-t','public.users','-t','public.user_oauth_identities'])
private_file(secret_dir/'schema-before.sql',schema.decode())

bootstrap = '''
import json,sys,os
import psycopg2
from psycopg2 import sql
payload=json.load(sys.stdin)
try:
    db=psycopg2.connect(os.environ['DATABASE_URL'],connect_timeout=5)
    with db, db.cursor() as cur:
        cur.execute("SET LOCAL lock_timeout='2s'; SET LOCAL statement_timeout='15s'")
        cur.execute(sql.SQL("CREATE ROLE admirra_registration_notifier LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 2").format(sql.Literal(payload['password'])))
        cur.execute("GRANT CONNECT ON DATABASE saas_project TO admirra_registration_notifier")
        cur.execute(payload['schema'])
        cur.execute(payload['grants'])
    db.close()
    print('Outbox and least-privilege role installed')
except Exception as e:
    print('Database install failed:',type(e).__name__)
    sys.exit(1)
'''
payload=json.dumps({'password':password,'schema':(root/'schema.sql').read_text(),'grants':(root/'grants.sql').read_text()})
result=command(['docker','exec','-i','admirra-backend-1','python','-c',bootstrap],input=payload.encode())
print(result.decode().strip())
private_file(root/'.env','NOTIFIER_IMAGE='+args.image+'\n')
print('Prepared. Queue records only NEW accounts; consumer not started yet.')
