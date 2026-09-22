"""Import the narrow legacy automation overlay without secrets or external IO."""
import subprocess

code = '''
import asyncio, os
from pathlib import Path
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
os.environ.update(DATABASE_URL='postgresql://test:test@127.0.0.1/test',
    SIGNUP_DISCOUNT_ENABLED='false', SIGNUP_DISCOUNT_PILOT_USER_IDS='',
    LOG_TO_STDOUT='true', SMTP_ENABLED='false', WW_TEST='1', WW_TEST_ID='signup-image-smoke')
for name in ('automation/main.py', 'core/models.py', 'backend_api/services/auth_mail.py',
             'backend_api/services/signup_discount.py', 'backend_api/services/signup_discount_mail.py'):
    compile(Path('/app', name).read_bytes(), name, 'exec')
from backend_api.services.signup_discount_mail import send_signup_discount_reminders
assert asyncio.run(send_signup_discount_reminders()) == 0
print('Legacy automation: compile/import and disabled no-IO reminder passed')
'''
subprocess.run(['docker', 'run', '--rm', '--pull', 'never', '--network', 'none',
    '--read-only', '--tmpfs', '/tmp:size=32m', '--memory', '384m', '--cpus', '0.5',
    '--cap-drop', 'ALL', '--entrypoint', 'python', 'admirra-automation:signup-20260922',
    '-B', '-c', code], check=True)
