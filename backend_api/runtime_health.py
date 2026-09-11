"""Dependency probes: no schema changes, credentials or provider calls."""
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.database import engine
from core.runtime import get_runtime

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
def live():
    return {"status": "ok", "release": os.getenv("APP_RELEASE", "unknown"), "role": get_runtime().role}


@router.get("/ready")
def ready():
    expected = os.getenv("EXPECTED_SCHEMA_REVISION", "").strip()
    if get_runtime().role == "api" and not expected:
        return JSONResponse({"status": "not_ready", "reason": "schema_configuration"}, status_code=503)
    try:
        with engine.connect() as connection:
            if connection.dialect.name == "postgresql":
                connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
                connection.execute(text("SET LOCAL lock_timeout = '1000ms'"))
            connection.execute(text("SELECT 1"))
            if expected:
                actual = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
                if actual != {expected}:
                    return JSONResponse({"status": "not_ready", "reason": "schema"}, status_code=503)
    except Exception:
        return JSONResponse({"status": "not_ready", "reason": "database"}, status_code=503)
    return live()
