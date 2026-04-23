"""Публичный домен Admirra: prod / dev через ADMIRRA_DEPLOY_ENV."""

from __future__ import annotations

from typing import Optional
from core.config import get_config


def deploy_env_raw() -> Optional[str]:
    v = get_config().public_domain.admierra_deploy_env
    if v is None or not str(v).strip():
        return None
    return str(v).strip().lower()


def deploy_env() -> str:
    """Для логов: явное значение или prod по умолчанию."""
    return deploy_env_raw() or "prod"


def public_host() -> str:
    override = (get_config().public_domain.admierra_public_host or "").strip()
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
    explicit = get_config().public_domain.frontend_url
    if explicit:
        return explicit.rstrip("/")

    d = deploy_env_raw()
    if d == "dev":
        return "https://admirra.online"
    if d == "prod":
        return "https://admirra.ru"
    return "http://localhost:5173"
