"""Фикстуры для тестов internal_admin."""
import os

from cryptography.fernet import Fernet

# Env до импорта приложения (core.database требует DATABASE_URL при загрузке).
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-min-32-chars")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("INTERNAL_ADMIN_ENABLED", "true")
os.environ.setdefault("INTERNAL_ADMIN_JWT_SECRET", "internal-admin-test-jwt-secret-key")
os.environ.setdefault("INTERNAL_ADMIN_OPENAI_USD_PER_1K_TOKENS", "0.002")
os.environ.setdefault("AUTH_LOGIN_OTP_ENABLED", "false")
os.environ.setdefault("AUTH_REQUIRE_EMAIL_VERIFIED", "false")

import bcrypt

if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (object,), {"__version__": getattr(bcrypt, "__version__", "4.0.1")})

from core.config import get_config

get_config.cache_clear()

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base, get_db
from core import models, security
import core.models as _core_models  # noqa: F401
import internal_admin.models as _ia_models  # noqa: F401
from internal_admin.router import router as internal_admin_router
from internal_admin.manager_router import router as internal_manager_router
from internal_admin.seo_router import router as internal_seo_router
from internal_admin.auth_public_router import router as internal_auth_public_router
from internal_admin.security import create_admin_access_token


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def admin_app(db):
    app = FastAPI()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    app.include_router(internal_admin_router, prefix="/api")
    app.include_router(internal_manager_router, prefix="/api")
    app.include_router(internal_seo_router, prefix="/api")
    app.include_router(internal_auth_public_router, prefix="/api")
    return app


@pytest.fixture()
def client(admin_app):
    with TestClient(admin_app) as c:
        yield c


def make_user(
    db,
    *,
    email: str,
    role: models.UserRole,
    password: str = "secret123",
    is_active: bool = True,
    **kwargs,
):
    user = models.User(
        email=email,
        password_hash=security.get_password_hash(password),
        role=role,
        is_active=is_active,
        email_verified=True,
        **kwargs,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def admin_auth_header(user: models.User, session_id: str | None = None) -> dict[str, str]:
    token = create_admin_access_token(user.id, user.email, user.role.value, session_id=session_id)
    return {"Authorization": f"Bearer {token}"}
