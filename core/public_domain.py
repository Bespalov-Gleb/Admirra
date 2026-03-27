"""Публичный домен Admirra: prod / dev через ADMIRRA_DEPLOY_ENV."""

from __future__ import annotations

import os
from typing import Optional


def deploy_env_raw() -> Optional[str]:
    v = os.getenv("ADMIRRA_DEPLOY_ENV")
    if v is None or not str(v).strip():
        return None
    return str(v).strip().lower()


def deploy_env() -> str:
    """Для логов: явное значение или prod по умолчанию."""
    return deploy_env_raw() or "prod"


def public_host() -> str:
    override = (os.getenv("ADMIRRA_PUBLIC_HOST") or "").strip()
    if override:
        return override.lstrip("/").replace("https://", "").replace("http://", "").split("/")[0]
    d = deploy_env_raw()
    if d == "dev":
        return "admirra.online"
    return "admirra.ru"


def public_origin() -> str:
    return f"https://{public_host()}"


def resolve_frontend_url() -> str:
    """
    URL фронта для ссылок из бэкенда (верификация email и т.п.).

    Приоритет:
    1. FRONTEND_URL — явно заданный URL (перекрывает всё).
    2. ADMIRRA_DEPLOY_ENV=dev → https://admirra.online
    3. ADMIRRA_DEPLOY_ENV=prod → https://admirra.ru
    4. переменная не задана — локальная разработка (Vite).
    """
    explicit = os.getenv("FRONTEND_URL")
    if explicit:
        return explicit.rstrip("/")

    d = deploy_env_raw()
    if d == "dev":
        return "https://admirra.online"
    if d == "prod":
        return "https://admirra.ru"
    return "http://localhost:5173"
