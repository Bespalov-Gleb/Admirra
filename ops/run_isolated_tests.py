"""Test entrypoint for a --network none container, never a production process."""
import base64
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


def main():
    if os.getenv("WW_TEST") != "1" or not os.getenv("WW_TEST_ID"):
        raise SystemExit("WW_TEST=1 and WW_TEST_ID are required")
    if Path(".env").exists():
        raise SystemExit("Refusing to test from an image/source tree containing .env")
    if urlsplit(os.getenv("DATABASE_URL", "")).hostname not in {"127.0.0.1", "localhost", "test-db"}:
        raise SystemExit("An explicitly isolated test database is required")
    os.environ["SECRET_KEY"] = "isolated-tests-not-a-production-secret"
    os.environ["ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"0" * 32).decode()
    os.environ["APP_PROCESS_ROLE"] = "test"
    os.environ["DB_AUTO_BOOTSTRAP"] = "false"
    os.environ["RUN_SYNC_WORKER"] = "false"
    os.environ["RUN_API_SCHEDULER"] = "false"
    os.environ["UPLOADS_DIR"] = "/tmp/admirra-test-uploads"
    os.environ["LOG_TO_STDOUT"] = "true"
    os.environ["REJECTED_LEADS_DIR"] = "/tmp/admirra-test-rejected-leads"
    os.environ["REDIS_ENABLED"] = "false"
    os.environ["SMTP_ENABLED"] = "false"
    import pytest
    raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", *sys.argv[1:]]))


if __name__ == "__main__":
    main()
