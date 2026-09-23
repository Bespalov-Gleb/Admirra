"""Prepare (never start) role-scoped runtime files via a private SSH pipe.

export runs on API1, install on worker host. stdout of export contains secrets
and MUST only be piped to install, never to a terminal or a log.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from ops.private_redis import write_once
from ops.service_credentials import validate

# Explicit allowlist: no login/admin/webhook/captcha/database-superuser secrets.
PREFIXES = ("BILLING_", "DETECTOR_", "AI_INPUT_", "AI_OUTPUT_", "AI_CACHE_",
            "DADATA_", "INFOTRACKPEOPLE_", "SMTP_", "UNISENDER_")
KEYS = set("""SECRET_KEY ENCRYPTION_KEY ADMIRRA_DEPLOY_ENV
YANDEX_CLIENT_ID YANDEX_CLIENT_SECRET YANDEX_ORG_CLIENT_ID YANDEX_ORG_CLIENT_SECRET
YANDEX_DIRECT_FINANCE_TOKEN VK_CLIENT_ID VK_CLIENT_SECRET VK_ADS_CLIENT_ID VK_ADS_CLIENT_SECRET
MYTARGET_CLIENT_ID MYTARGET_CLIENT_SECRET MYTARGET_API_URL
AVITO_CLIENT_ID AVITO_CLIENT_SECRET OPENAI_API_KEY OPENAI_BASE_URL OPENAI_MODEL AI_PROXY_URL
OPENROUTER_API_KEY OPENROUTER_BASE_URL OPENROUTER_DEFAULT_MODEL OPENROUTER_REFERER OPENROUTER_TITLE
AI_COMMENT_MODEL AI_API_TIMEOUT_SECONDS
CLOUDPAYMENTS_API_SECRET CLOUDPAYMENTS_PUBLIC_ID CLOUDPAYMENTS_CURRENCY
CLOUDPAYMENTS_RECEIPT_TAXATION_SYSTEM CLOUDPAYMENTS_RECEIPT_VAT
CLOUDPAYMENTS_RECEIPT_METHOD CLOUDPAYMENTS_RECEIPT_OBJECT
MAX_API_BASE MAX_REPORTS_BOT_TOKEN MAX_REPORTS_BOT_NAME
TELEGRAM_ENABLED TELEGRAM_BOT_TOKEN TELEGRAM_BOT_USERNAME TELEGRAM_CHAT_ID
TELEGRAM_API_BASE TELEGRAM_API_VERIFY METRIKA_COUNTER_ID METRIKA_OFFLINE_TOKEN
AUTO_SYNC_HOUR_MSK AUTO_REPORTS_HOUR_MSK AUTO_SYNC_DAYS
SIGNUP_DISCOUNT_ENABLED SIGNUP_DISCOUNT_PILOT_USER_IDS""".split())
EXCLUDED = {"SMTP_DIAGNOSE_SECRET", "BILLING_ADMIN_WHITELIST"}
AI_KEYS = {k for k in KEYS if k.startswith("OPENROUTER_")} | {"AI_COMMENT_MODEL", "AI_API_TIMEOUT_SECONDS"}


def runtime_payload(automation_env, backend_env, google):
    """Comments execute in backend today: never take its new provider from legacy automation."""
    for key in ("SECRET_KEY", "ENCRYPTION_KEY"):
        if not automation_env.get(key) or automation_env[key] != backend_env.get(key):
            raise ValueError("Backend/automation auth material differs")
    values = select(automation_env)
    for key in AI_KEYS:
        values.pop(key, None)
        if key in backend_env:
            values[key] = backend_env[key]
    if not values.get("OPENROUTER_API_KEY") or not values.get("OPENROUTER_BASE_URL"):
        raise ValueError("Backend comment provider is not configured")
    return {"env": values, "google": google}


def refresh_ai(payload, root=Path("/etc/admirra")):
    """Explicit narrow update; never replace DB, scheduler or unrelated provider credentials."""
    if set(payload) != {"env", "google"} or select(payload["env"]) != payload["env"]:
        raise ValueError("Unexpected runtime payload")
    path = root / "worker.env"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Existing regular worker env required")
    original = path.read_text()
    current = dict(line.split("=", 1) for line in original.splitlines() if line)
    incoming = payload["env"]
    if any(current.get(k) != incoming.get(k) for k in ("SECRET_KEY", "ENCRYPTION_KEY")):
        raise ValueError("Auth/encryption material mismatch")
    if not incoming.get("OPENROUTER_API_KEY") or not incoming.get("OPENROUTER_BASE_URL"):
        raise ValueError("Missing comment provider credentials")
    for key in AI_KEYS:
        current.pop(key, None)
        if key in incoming:
            current[key] = incoming[key]
    updated = env_text(current)
    if updated == original:
        return
    backup = root / ("worker.env.before-ai-" + hashlib.sha256(original.encode()).hexdigest()[:12])
    write_once(backup, original, 0o600)
    pending = root / "worker.env.ai-next"
    write_once(pending, updated, 0o600)
    os.replace(pending, path)


def select(source):
    result = {k: v for k, v in source.items()
              if (k in KEYS or k.startswith(PREFIXES)) and k not in EXCLUDED}
    for key in ("SECRET_KEY", "ENCRYPTION_KEY"):
        if not result.get(key):
            raise ValueError("Missing runtime encryption/auth material")
    return result


def env_text(values):
    # Compose env_file format: raw prevents $, # and quotes being reinterpreted.
    if any(not isinstance(v, str) or any(c in v for c in "\r\n\x00") for v in values.values()):
        raise ValueError("Multiline/NUL runtime values are not supported")
    return "".join(f"{k}={v}\n" for k, v in sorted(values.items()))


def install(payload, root=Path("/etc/admirra")):
    if set(payload) != {"env", "google"} or select(payload["env"]) != payload["env"]:
        raise ValueError("Unexpected runtime payload")
    db = (root / "db-worker.env").read_text()
    validate("db-worker", db)
    values = dict(payload["env"])
    values.update(line.split("=", 1) for line in db.splitlines() if line)
    values["GOOGLE_APPLICATION_CREDENTIALS"] = "/app/secrets/google-service-account.json"
    write_once(root / "worker.env", env_text(values), 0o600)
    # Calendar/outbox only: no business-provider credentials, storage or files.
    write_once(root / "scheduler.env", db, 0o600)
    secret_dir = root / "worker-secrets"
    secret_dir.mkdir(mode=0o750, exist_ok=True)
    if secret_dir.is_symlink():
        raise ValueError("Unexpected secret directory")
    google = json.loads(payload["google"])
    if google.get("type") != "service_account" or not google.get("private_key"):
        raise ValueError("Invalid service account")
    write_once(secret_dir / "google-service-account.json", payload["google"], 0o640)
    if os.geteuid() == 0:
        os.chown(secret_dir, 0, 10001)
        os.chown(secret_dir / "google-service-account.json", 0, 10001)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "install", "refresh-ai"))
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Root required")
    if args.action == "export":
        if sys.stdout.isatty():
            raise SystemExit("Secrets must be piped directly to the target")
        runtime = json.loads(subprocess.check_output(["docker", "inspect", "admirra-automation-1"]))[0]
        env = dict(row.split("=", 1) for row in runtime["Config"]["Env"])
        backend = json.loads(subprocess.check_output(["docker", "inspect", "admirra-backend-1"]))[0]
        backend_env = dict(row.split("=", 1) for row in backend["Config"]["Env"])
        print(json.dumps(runtime_payload(env, backend_env, Path("/root/Admirra/secrets/google-service-account.json").read_text())))
    else:
        raw = sys.stdin.buffer.read(131073)
        if len(raw) > 131072:
            raise SystemExit("Unexpected payload size")
        (refresh_ai if args.action == "refresh-ai" else install)(json.loads(raw))
        print("Worker and scheduler environment prepared; secrets not emitted; no services started")


if __name__ == "__main__":
    main()
