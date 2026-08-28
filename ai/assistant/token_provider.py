"""Провайдер доступа к Yandex API для конкретного проекта (client_id).

Берёт Yandex Direct интеграцию проекта (её OAuth-токен несёт scope
`direct:api metrika:read` — на чтение и Директа, и Метрики), расшифровывает
токен и умеет его обновлять на 401 тем же приложением (org/основное), сохраняя
результат в БД. Логика повторяет synk (automation/sync.py)."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core import models, security
from core.config import get_config

logger = logging.getLogger("ai_assistant.token_provider")
cfg = get_config()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class YandexAccessError(RuntimeError):
    """Нет пригодной Яндекс-интеграции у проекта (не подключена/без токена)."""


class VkAccessError(RuntimeError):
    """Нет пригодной VK Ads интеграции у проекта."""


class AvitoAccessError(RuntimeError):
    """Нет пригодной Avito Ads интеграции у проекта."""


def _clean_profile_login(value: Optional[str]) -> Optional[str]:
    profile = str(value or "").strip()
    if not profile or profile.lower() in {"unknown", "none"}:
        return None
    return profile


def _selected_profile(integration: models.Integration) -> Optional[str]:
    """Client-Login профиля (для агентских токенов) — как в sync/stats."""
    if getattr(integration, "is_agency", False):
        profile = integration.agency_client_login or integration.account_id
    else:
        profile = integration.account_id
    return _clean_profile_login(profile)


def _app_credentials(integration: models.Integration) -> tuple[str, str]:
    """client_id/secret приложения, которым выдан токен (org или основное)."""
    if getattr(integration, "oauth_app", None) == "org":
        return cfg.oauth.yandex_org_client_id, cfg.oauth.yandex_org_client_secret
    return cfg.oauth.yandex_client_id, cfg.oauth.yandex_client_secret


def _counter_ids(integration: models.Integration) -> list[str]:
    raw = integration.selected_counters
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else (raw or [])
        return [str(c) for c in parsed if str(c).strip()]
    except (json.JSONDecodeError, TypeError):
        return []


def _goal_ids(integration: models.Integration) -> list[str]:
    """Отслеживаемые цели проекта — те же, что на дашборде: selected_goals +
    primary_goal_id (логика как в backend_api/stats.py)."""
    raw = integration.selected_goals
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else (raw or [])
        goals = [str(g) for g in parsed if str(g).strip()]
    except (json.JSONDecodeError, TypeError):
        goals = []
    primary = str(integration.primary_goal_id or "").strip()
    if primary and primary not in goals:
        goals.append(primary)
    return goals


@dataclass
class YandexAccess:
    """Живой доступ к Яндекс API одного проекта. Держит расшифрованный токен и
    умеет рефрешить его при истечении."""
    db: Session
    integration: models.Integration
    client_login: Optional[str]
    counter_ids: list[str] = field(default_factory=list)
    goal_ids: list[str] = field(default_factory=list)  # отслеживаемые цели (дашборд)
    _token: Optional[str] = None

    @property
    def account_name(self) -> Optional[str]:
        return self.integration.account_name

    def access_token(self) -> str:
        if self._token is None:
            enc = self.integration.access_token
            if not enc:
                raise YandexAccessError("У Яндекс-интеграции проекта нет access_token")
            self._token = security.decrypt_token(enc)
        return self._token

    async def refresh(self) -> str:
        """Обновляет access_token по refresh_token тем же приложением и
        сохраняет в БД. Вызывается при 401 от Яндекса."""
        from backend_api.services import IntegrationService

        enc_rt = self.integration.refresh_token
        if not enc_rt:
            raise YandexAccessError("Нет refresh_token — токен не обновить")
        rt = security.decrypt_token(enc_rt)
        app_id, app_secret = _app_credentials(self.integration)
        data = await IntegrationService.refresh_yandex_token(rt, app_id, app_secret)
        if not data or "access_token" not in data:
            raise YandexAccessError("Не удалось обновить токен Яндекса")
        self.integration.access_token = security.encrypt_token(data["access_token"])
        if data.get("refresh_token"):
            self.integration.refresh_token = security.encrypt_token(data["refresh_token"])
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to persist refreshed Yandex token")
        self._token = data["access_token"]
        return self._token


def resolve_yandex(db: Session, client_id: UUID | str) -> YandexAccess:
    """Возвращает YandexAccess для проекта или бросает YandexAccessError.

    Берёт активную Yandex Direct интеграцию с access_token. Именно её токен
    используется и для Директа, и для Метрики (единый OAuth проекта)."""
    q = (
        db.query(models.Integration)
        .filter(
            models.Integration.client_id == client_id,
            models.Integration.platform == models.IntegrationPlatform.YANDEX_DIRECT,
            models.Integration.access_token.isnot(None),
        )
    )
    integrations = q.all()
    # Приоритет активным подключениям.
    integration = next(
        (i for i in integrations if getattr(i, "connection_status", "active") == "active"),
        integrations[0] if integrations else None,
    )
    if integration is None:
        raise YandexAccessError(
            "К проекту не подключён Яндекс.Директ — ассистенту нечего анализировать"
        )
    return YandexAccess(
        db=db,
        integration=integration,
        client_login=_selected_profile(integration),
        counter_ids=_counter_ids(integration),
        goal_ids=_goal_ids(integration),
    )


def has_yandex(db: Session, client_id: UUID | str) -> bool:
    try:
        resolve_yandex(db, client_id)
        return True
    except YandexAccessError:
        return False


# ── Общий поиск активной интеграции платформы ────────────────────────────────
def _active_integration(db: Session, client_id, platform: "models.IntegrationPlatform"):
    rows = (
        db.query(models.Integration)
        .filter(models.Integration.client_id == client_id, models.Integration.platform == platform)
        .all()
    )
    return next(
        (i for i in rows if getattr(i, "connection_status", "active") == "active"),
        rows[0] if rows else None,
    )


# ── VK Ads ───────────────────────────────────────────────────────────────────
@dataclass
class VkAccess:
    """Живой доступ к VK Ads одного проекта. VK access-токен живёт ~1 час,
    поэтому перед вызовом обновляем его по refresh_token, если истёк."""
    db: Session
    integration: models.Integration

    @property
    def account_name(self) -> Optional[str]:
        return self.integration.account_name

    async def _ensure_fresh(self) -> None:
        exp = self.integration.expires_at
        if not exp or _aware(exp) > _now() + timedelta(minutes=2):
            return
        if not self.integration.refresh_token:
            return
        from backend_api.integrations import VK_CLIENT_ID, VK_CLIENT_SECRET
        from backend_api.services import IntegrationService
        rt = security.decrypt_token(self.integration.refresh_token)
        data = await IntegrationService.refresh_vk_token(rt, VK_CLIENT_ID, VK_CLIENT_SECRET)
        if not data or not data.get("access_token"):
            return
        self.integration.access_token = security.encrypt_token(data["access_token"])
        if data.get("refresh_token"):
            self.integration.refresh_token = security.encrypt_token(data["refresh_token"])
        if data.get("expires_in"):
            self.integration.expires_at = _now() + timedelta(seconds=int(data["expires_in"]))
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to persist refreshed VK token")

    async def api(self):
        """Свежий VKAdsAPI проекта (с актуальным токеном)."""
        await self._ensure_fresh()
        from automation.vk_ads import VKAdsAPI
        token = security.decrypt_token(self.integration.access_token)
        return VKAdsAPI(token, self.integration.account_id, send_client_id=False)


def resolve_vk(db: Session, client_id: UUID | str) -> VkAccess:
    integration = _active_integration(db, client_id, models.IntegrationPlatform.VK_ADS)
    if integration is None or not integration.access_token:
        raise VkAccessError("К проекту не подключён VK Ads")
    return VkAccess(db=db, integration=integration)


# ── Avito Ads ────────────────────────────────────────────────────────────────
@dataclass
class AvitoAccess:
    """Живой доступ к Avito Ads одного проекта. AvitoAdsAPI сам держит bearer по
    client_credentials, отдельный рефреш не нужен."""
    db: Session
    integration: models.Integration

    @property
    def account_name(self) -> Optional[str]:
        return self.integration.account_name

    def api(self):
        from automation.avito_integration_helpers import build_avito_api_from_integration
        try:
            return build_avito_api_from_integration(self.integration)
        except ValueError as exc:
            raise AvitoAccessError(str(exc)) from exc


def resolve_avito(db: Session, client_id: UUID | str) -> AvitoAccess:
    integration = _active_integration(db, client_id, models.IntegrationPlatform.AVITO_ADS)
    if integration is None or not (integration.platform_client_id and integration.platform_client_secret):
        raise AvitoAccessError("К проекту не подключён Avito Ads")
    return AvitoAccess(db=db, integration=integration)


def available_platforms(db: Session, client_id: UUID | str) -> dict:
    """Какие рекламные платформы реально подключены у проекта (для агента)."""
    return {
        "yandex": has_yandex(db, client_id),
        "vk": _has(db, client_id, resolve_vk, VkAccessError),
        "avito": _has(db, client_id, resolve_avito, AvitoAccessError),
    }


def _has(db, client_id, resolver, err_type) -> bool:
    try:
        resolver(db, client_id)
        return True
    except err_type:
        return False
