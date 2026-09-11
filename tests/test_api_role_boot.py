"""Run a fresh interpreter so other tests cannot mask import-time side effects."""
import os
import subprocess
import sys


def test_api_import_and_lifespan_never_bootstrap_or_start_sync():
    script = '''
import sqlalchemy
attempts = []
def forbidden(*args, **kwargs):
    attempts.append(True)
    raise AssertionError("API startup attempted a database connection")
sqlalchemy.engine.Engine.connect = forbidden
from backend_api.main import app
from fastapi.testclient import TestClient
import backend_api.sync_jobs as jobs
with TestClient(app) as client:
    assert attempts == [], "API import/startup attempted a database connection"
    assert client.get('/api/health/live').status_code == 200
    assert client.get('/api/health/ready').status_code == 503
    jobs.ensure_sync_worker_started()
    assert jobs._worker_started is False
    from backend_api.main import lead_scheduler
    assert lead_scheduler is None
'''
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            timeout=30, env={**os.environ, "APP_PROCESS_ROLE": "api",
                                            "DB_AUTO_BOOTSTRAP": "false", "RUN_SYNC_WORKER": "false",
                                            "RUN_API_SCHEDULER": "false"})
    assert result.returncode == 0, result.stderr[-5000:]
