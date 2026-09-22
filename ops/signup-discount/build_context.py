"""Assemble a narrow overlay, preserving the deployed code outside this feature.

Usage: python3 ops/signup-discount/build_context.py /private/tmp/admirra-signup-release
The active backend sources must first be exported to BASE/base (no env files).
The frontend tree must be a clean git archive, not the dirty working tree.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = '960f7279fd3c1717c52bcd342ff1db8559962acd'
DEST = Path(sys.argv[1]).resolve()
BACKEND = (
    'backend_api/billing.py', 'backend_api/services/auth_mail.py',
    'backend_api/services/promo.py', 'core/models.py', 'core/pricing.py', 'core/schemas.py',
)
NEW = (
    'backend_api/services/purchase_analytics.py', 'backend_api/services/signup_discount.py',
    'backend_api/services/signup_discount_mail.py',
)
FRONT = Path('admin-panel-vue-main/admin-panel-vue-main')
FRONT_FILES = (
    'index.html', 'src/composables/useBillingCloudPayments.js', 'src/layouts/MockupLayout.vue',
    'src/utils/metrika.js', 'src/utils/purchaseAnalytics.js', 'src/utils/discountStrip.js', 'src/components/SignupDiscount.vue',
    'src/views/Auth/OAuthLoginCallback.vue', 'src/views/Auth/SignUp.vue', 'src/views/Tariffs/TariffsPage.vue',
)

def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Source context drift')
    return text.replace(old, new, 1)

def copy(path):
    target = DEST / 'backend' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / path, target)

hashes = {}
for path in BACKEND:
    active = (DEST / 'base' / path).read_bytes()
    tracked = subprocess.check_output(['git', 'show', BASE_COMMIT + ':' + path], cwd=ROOT)
    if active != tracked:
        raise RuntimeError('Active backend differs from reviewed HEAD: ' + path)
    hashes[path] = hashlib.sha256(active).hexdigest()
    copy(path)
for path in NEW:
    copy(path)

# Do not carry the pending durable-sync/API query changes into production.
path = 'backend_api/integrations.py'
active = (DEST / 'base' / path).read_text()
hashes[path] = hashlib.sha256((DEST / 'base' / path).read_bytes()).hexdigest()
active = once(active, '    log_event("backend", f"updated integration {integration_id}", integration_in)',
    '    if integration_in.get("is_active") is True:\n'
    '        from backend_api.services.signup_discount import grant_for_integration\n'
    '        grant_for_integration(db, integration, finalized=True)\n'
    '    log_event("backend", f"updated integration {integration_id}", integration_in)')
active = once(active, '        db.add(new_integration)\n        db.commit()\n        \n        # 3. Trigger initial sync',
    '        db.add(new_integration)\n'
    '        from backend_api.services.signup_discount import grant_for_integration\n'
    '        db.flush()\n'
    '        grant_for_integration(db, new_integration, finalized=True)\n'
    '        db.commit()\n        \n        # 3. Trigger initial sync')
(DEST / 'backend' / path).write_text(active)

automation = DEST / 'automation'
for path in ('automation/main.py', 'core/models.py'):
    base_path = DEST / 'automation-base' / path
    text = base_path.read_text()
    hashes['automation:' + path] = hashlib.sha256(base_path.read_bytes()).hexdigest()
    if path == 'core/models.py':
        fields = (ROOT / path).read_text().split('    signup_discount_granted_at = ', 1)[1].split('    ai_requests_used = ', 1)[0]
        text = once(text, '    ai_requests_used = Column(Integer, nullable=False, default=0)\n',
            '    signup_discount_granted_at = ' + fields + '    ai_requests_used = Column(Integer, nullable=False, default=0)\n')
    else:
        text = once(text, '    scheduler.start()\n',
            "    from backend_api.services.signup_discount_mail import send_signup_discount_reminders\n"
            "    scheduler.add_job(send_signup_discount_reminders, 'interval', minutes=10,\n"
            "                      id='signup_discount_reminders', max_instances=1, coalesce=True)\n"
            "    scheduler.start()\n")
    target = automation / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
for path in ('backend_api/services/signup_discount.py', 'backend_api/services/signup_discount_mail.py', 'backend_api/services/auth_mail.py'):
    target = automation / path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / path, target)

frontend = DEST / 'frontend' / FRONT
for path in FRONT_FILES:
    shutil.copyfile(ROOT / FRONT / path, frontend / path)
# MainLayout has unrelated in-progress support-mode edits. Component itself
# suppresses the discount UI during impersonation, so those edits aren't needed.
main = frontend / 'src/layouts/MainLayout.vue'
text = subprocess.check_output(['git', 'show', BASE_COMMIT + ':' + str(FRONT / 'src/layouts/MainLayout.vue')], cwd=ROOT).decode()
text = once(text, '      </header>\n', '      </header>\n      <SignupDiscount />\n')
text = once(text, "import Header from '../components/Header.vue'", "import Header from '../components/Header.vue'\nimport SignupDiscount from '../components/SignupDiscount.vue'")
main.write_text(text)
(DEST / 'source-manifest.json').write_text(json.dumps({'base_sha256': hashes, 'backend_files': [*BACKEND, *NEW, 'backend_api/integrations.py'], 'frontend_files': FRONT_FILES}, indent=2))
print('Scoped backend overlay and clean frontend source prepared')
