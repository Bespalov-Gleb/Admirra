"""
Вход и регистрация через Яндекс ID и VK.

- Яндекс: OAuth приложения Директа / login.
- VK: вход на сайт — OAuth 2.1 VK ID (id.vk.ru), PKCE, обмен кода на бэкенде.
  См. https://id.vk.com/about/business/go/docs/ru/vkid/latest/vk-id/connection/start-integration/auth-without-sdk/auth-without-sdk-web
  Интеграция VK Ads по-прежнему: ads.vk.com и backend_api/integrations.

redirect_uri может совпадать с callback интеграций (/auth/yandex/callback, /auth/vk/callback):
фронт помечает вход в sessionStorage и после возврата вызывает эти эндпоинты, а не exchange интеграции.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import models, schemas, security
from core.config import get_config
from core.database import get_db

from backend_api.services.subscription import SubscriptionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/oauth", tags=["OAuth Login"])

cfg = get_config()
SECRET_KEY = cfg.security.secret_key
ALGORITHM = "HS256"

YANDEX_CLIENT_ID = cfg.oauth.yandex_client_id
YANDEX_CLIENT_SECRET = cfg.oauth.yandex_client_secret
YANDEX_AUTH_URL = cfg.oauth.yandex_auth_url
YANDEX_TOKEN_URL = cfg.oauth.yandex_token_url

# Вход: OAuth 2.1 VK ID; client_id из кабинета VK ID (id.vk.com). При пустом VK_LOGIN_CLIENT_ID — VK_CLIENT_ID.
VK_LOGIN_CLIENT_ID = (cfg.oauth.vk_login_client_id or cfg.oauth.vk_client_id or "").strip()
VK_LOGIN_SCOPE = (cfg.oauth.vk_login_scope or "").strip()
VK_ID_BASE = (cfg.oauth.vk_id_oauth_base or "https://id.vk.ru").rstrip("/")

_VK_ID_LOGIN_LOCK = threading.Lock()
# state (строка из authorize) -> { verifier, exp } для обмена кода на токен (один инстанс воркера; при нескольких — нужен Redis).
_VK_ID_LOGIN_PENDING: dict[str, dict] = {}

# Только профиль для входа в приложение (отдельно от direct:api при подключении Директа)
YANDEX_LOGIN_SCOPE = "login:email login:info"


def _oauth_state_prefix(provider: str) -> str:
    return "site-yandex." if provider == "yandex" else "site-vk."


def _sign_oauth_state(provider: str) -> str:
    """
    Подписанный state для Яндекса (и совместимости). VK ID использует отдельный случайный state + PKCE в vk_oauth_authorize_url.
    """
    exp = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
    nonce = secrets.token_hex(16)
    msg = f"{provider}|{exp}|{nonce}"
    mac = hmac.new(
        SECRET_KEY.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    inner = f"{exp}|{nonce}|{mac}"
    inner_b64 = base64.urlsafe_b64encode(inner.encode("utf-8")).decode("ascii").rstrip("=")
    return _oauth_state_prefix(provider) + inner_b64


def _verify_oauth_state_compact(b64_inner: str, provider: str) -> None:
    pad = "=" * (-len(b64_inner) % 4)
    try:
        inner = base64.urlsafe_b64decode(b64_inner + pad).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")
    parts = inner.split("|")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")
    exp_s, nonce, mac = parts
    try:
        exp = int(exp_s)
    except ValueError:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")
    if int(datetime.utcnow().timestamp()) > exp:
        raise HTTPException(status_code=400, detail="Истёк параметр state, войдите снова")
    msg = f"{provider}|{exp_s}|{nonce}"
    expect = hmac.new(
        SECRET_KEY.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(mac, expect):
        raise HTTPException(status_code=400, detail="Недействительный параметр state")


def _verify_oauth_state_jwt(state: str, provider: str) -> None:
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")
    if payload.get("pur") != "oauth_login" or payload.get("prv") != provider:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")


def _verify_oauth_state(state: str, provider: str) -> None:
    prefix = _oauth_state_prefix(provider)
    if state.startswith(prefix):
        _verify_oauth_state_compact(state[len(prefix) :], provider)
        return
    if state.count(".") == 2:
        _verify_oauth_state_jwt(state, provider)
        return
    raise HTTPException(status_code=400, detail="Недействительный параметр state")


def _pkce_challenge(verifier: str) -> str:
    d = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(d).decode("ascii").rstrip("=")


def _vk_id_pending_cleanup_locked() -> None:
    now = time.time()
    dead = [k for k, v in _VK_ID_LOGIN_PENDING.items() if v["exp"] < now]
    for k in dead:
        del _VK_ID_LOGIN_PENDING[k]


def _vk_id_pending_put(state_key: str, verifier: str) -> None:
    with _VK_ID_LOGIN_LOCK:
        _vk_id_pending_cleanup_locked()
        _VK_ID_LOGIN_PENDING[state_key] = {"verifier": verifier, "exp": time.time() + 900}


def _vk_id_pending_pop(state_key: str) -> Optional[str]:
    with _VK_ID_LOGIN_LOCK:
        _vk_id_pending_cleanup_locked()
        row = _VK_ID_LOGIN_PENDING.pop(state_key, None)
    if not row or row["exp"] < time.time():
        return None
    return row["verifier"]


def _synthetic_email(prefix: str, provider_uid: str) -> str:
    domain = (cfg.auth.oauth_login_synthetic_email_domain or "oauth-login.localhost").strip().lower()
    safe_uid = "".join(c if c.isalnum() else "_" for c in str(provider_uid))[:80]
    return f"{prefix}_{safe_uid}@{domain}"


def _issue_token_for_user(user: models.User) -> schemas.Token:
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


def _pick_username(db: Session, login: Optional[str]) -> Optional[str]:
    if not login:
        return None
    taken = db.query(models.User).filter(models.User.username == login).first()
    return None if taken else login


def _attach_identity(
    db: Session,
    user: models.User,
    provider: str,
    provider_user_id: str,
) -> None:
    existing = (
        db.query(models.UserOAuthIdentity)
        .filter(
            models.UserOAuthIdentity.provider == provider,
            models.UserOAuthIdentity.provider_user_id == provider_user_id,
        )
        .first()
    )
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(
                status_code=409,
                detail="Этот аккаунт уже привязан к другому пользователю",
            )
        return
    other_provider = (
        db.query(models.UserOAuthIdentity)
        .filter(
            models.UserOAuthIdentity.user_id == user.id,
            models.UserOAuthIdentity.provider == provider,
        )
        .first()
    )
    if other_provider:
        raise HTTPException(
            status_code=409,
            detail=f"Уже привязан другой аккаунт {provider}",
        )
    db.add(
        models.UserOAuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
    )


async def _yandex_exchange_code(code: str, redirect_uri: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            YANDEX_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": YANDEX_CLIENT_ID,
                "client_secret": YANDEX_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
            },
            timeout=30.0,
        )
        if r.status_code != 200:
            logger.warning("Yandex token exchange failed: %s %s", r.status_code, r.text[:300])
            raise HTTPException(status_code=400, detail="Не удалось обменять код Яндекса на токен")
        data = r.json()
        token = data.get("access_token")
        if not token:
            raise HTTPException(status_code=400, detail="Яндекс не вернул access_token")
        return token


async def _yandex_login_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://login.yandex.ru/info",
            headers={"Authorization": f"OAuth {access_token}"},
            timeout=15.0,
        )
        if r.status_code != 200:
            logger.warning("Yandex login info failed: %s %s", r.status_code, r.text[:300])
            raise HTTPException(status_code=400, detail="Не удалось получить профиль Яндекса")
        return r.json()


async def _vk_id_exchange_code(
    *,
    code: str,
    redirect_uri: str,
    state: str,
    device_id: str,
    code_verifier: str,
) -> dict:
    """Обмен authorization_code на токены VK ID (POST .../oauth2/auth)."""
    url = f"{VK_ID_BASE}/oauth2/auth"
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "client_id": VK_LOGIN_CLIENT_ID,
        "device_id": device_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, data=form, timeout=30.0)
    try:
        data = r.json()
    except Exception:
        logger.warning("VK ID oauth2/auth: non-JSON %s %s", r.status_code, r.text[:300])
        raise HTTPException(status_code=400, detail="Не удалось обменять код VK ID на токен")
    if data.get("error"):
        err = data.get("error_description") or data.get("error")
        logger.warning("VK ID oauth2/auth error: %s", err)
        raise HTTPException(status_code=400, detail=str(err) if err else "Ошибка VK ID OAuth")
    if not data.get("access_token"):
        logger.warning("VK ID: no access_token, keys=%s", list(data.keys()))
        raise HTTPException(status_code=400, detail="VK ID не вернул access_token")
    return data


async def _vk_id_user_info(access_token: str) -> dict:
    url = f"{VK_ID_BASE}/oauth2/user_info"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            data={"access_token": access_token, "client_id": VK_LOGIN_CLIENT_ID},
            timeout=15.0,
        )
    if r.status_code != 200:
        logger.warning("VK ID user_info failed: %s %s", r.status_code, r.text[:300])
        return {}
    try:
        return r.json()
    except Exception:
        return {}


def _find_user_by_email_ci(db: Session, email: str) -> Optional[models.User]:
    if not email:
        return None
    e = email.strip().lower()
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == e)
        .first()
    )


@router.get("/yandex/authorize-url", response_model=schemas.OAuthAuthorizeUrlResponse)
def yandex_oauth_authorize_url(redirect_uri: str):
    """
    redirect_uri — зарегистрированный в кабинете Яндекс OAuth (часто тот же, что у Директа:
    https://app.example.com/auth/yandex/callback).
    """
    if not YANDEX_CLIENT_ID or not YANDEX_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Яндекс OAuth не настроен на сервере")
    state = _sign_oauth_state("yandex")
    enc_redirect = quote(redirect_uri, safe="")
    enc_scope = quote(YANDEX_LOGIN_SCOPE, safe="")
    enc_state = quote(state, safe="")
    url = (
        f"{YANDEX_AUTH_URL}?response_type=code&client_id={YANDEX_CLIENT_ID}"
        f"&redirect_uri={enc_redirect}&scope={enc_scope}&state={enc_state}"
    )
    return {"url": url}


@router.post("/yandex/callback", response_model=schemas.Token)
async def yandex_oauth_callback(body: schemas.OAuthLoginCallbackRequest, db: Session = Depends(get_db)):
    _verify_oauth_state(body.state, "yandex")
    access_token = await _yandex_exchange_code(body.code.strip(), body.redirect_uri.strip())
    info = await _yandex_login_info(access_token)
    yandex_uid = str(info.get("id") or "").strip()
    if not yandex_uid:
        raise HTTPException(status_code=400, detail="В ответе Яндекса нет id пользователя")

    email = (info.get("default_email") or "").strip() or None
    login = (info.get("login") or "").strip()
    display_name = (info.get("display_name") or info.get("real_name") or "").strip()
    first_name = None
    last_name = None
    if display_name:
        parts = display_name.split(None, 1)
        first_name = parts[0] if parts else None
        last_name = parts[1] if len(parts) > 1 else None

    if not email:
        email = _synthetic_email("yandex", yandex_uid)

    identity = (
        db.query(models.UserOAuthIdentity)
        .filter(
            models.UserOAuthIdentity.provider == "yandex",
            models.UserOAuthIdentity.provider_user_id == yandex_uid,
        )
        .first()
    )
    if identity:
        user = db.query(models.User).filter(models.User.id == identity.user_id).first()
        if not user:
            raise HTTPException(status_code=500, detail="Пользователь не найден")
        return _issue_token_for_user(user)

    user = _find_user_by_email_ci(db, email)
    if user:
        _attach_identity(db, user, "yandex", yandex_uid)
        user.email_verified = True
        if first_name and not user.first_name:
            user.first_name = first_name
        if last_name and not user.last_name:
            user.last_name = last_name
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Не удалось привязать Яндекс к аккаунту",
            )
        return _issue_token_for_user(user)

    pwd = secrets.token_urlsafe(48)
    user = models.User(
        email=email,
        username=_pick_username(db, login),
        first_name=first_name,
        last_name=last_name,
        password_hash=security.get_password_hash(pwd),
        role=models.UserRole.MANAGER,
        email_verified=True,
        email_verification_token_hash=None,
        email_verification_expires_at=None,
    )
    db.add(user)
    db.flush()
    db.add(
        models.UserOAuthIdentity(
            user_id=user.id,
            provider="yandex",
            provider_user_id=yandex_uid,
        )
    )
    SubscriptionService.ensure_default_subscription(db, user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Не удалось создать аккаунт: конфликт данных (возможно, email уже занят)",
        )
    db.refresh(user)
    return _issue_token_for_user(user)


@router.get("/vk/authorize-url", response_model=schemas.OAuthAuthorizeUrlResponse)
def vk_oauth_authorize_url(redirect_uri: str):
    """
    Редирект на VK ID OAuth 2.1 (id.vk.ru/authorize), PKCE, без устаревшего oauth.vk.com.

    Приложение создаётся в кабинете VK ID; в доверенные redirect URI добавьте https://.../auth/vk/callback.
    """
    if not VK_LOGIN_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Вход через VK ID: задайте VK_LOGIN_CLIENT_ID или VK_CLIENT_ID (приложение из кабинета VK ID)",
        )
    # RFC 7636 / VK ID: verifier 43–128 символов [a-zA-Z0-9_-]
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = _pkce_challenge(code_verifier)
    # state: случайная строка ≥32 символов, только допустимые символы VK ID
    ext_state = secrets.token_urlsafe(32)
    _vk_id_pending_put(ext_state, code_verifier)

    scope = VK_LOGIN_SCOPE.replace(",", " ").strip()
    if not scope:
        scope = "vkid.personal_info email"

    q = [
        "response_type=code",
        f"client_id={quote(VK_LOGIN_CLIENT_ID, safe='')}",
        f"redirect_uri={quote(redirect_uri, safe='')}",
        f"state={quote(ext_state, safe='')}",
        f"code_challenge={quote(code_challenge, safe='')}",
        "code_challenge_method=S256",
        f"scope={quote(scope, safe='')}",
    ]
    url = f"{VK_ID_BASE}/authorize?{'&'.join(q)}"
    return {"url": url}


@router.post("/vk/callback", response_model=schemas.Token)
async def vk_oauth_callback(body: schemas.OAuthLoginCallbackRequest, db: Session = Depends(get_db)):
    if not VK_LOGIN_CLIENT_ID:
        raise HTTPException(status_code=503, detail="VK ID для входа не настроен (VK_LOGIN_CLIENT_ID / VK_CLIENT_ID)")

    state_key = body.state.strip()
    code_verifier = _vk_id_pending_pop(state_key)
    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="Сессия входа VK ID истекла или уже использована. Откройте «Войти через VK» снова.",
        )

    device_id = (body.device_id or "").strip()
    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="Не передан device_id. Обновите фронт: после VK ID в URL приходит параметр payload.",
        )

    token_data = await _vk_id_exchange_code(
        code=body.code.strip(),
        redirect_uri=body.redirect_uri.strip(),
        state=state_key,
        device_id=device_id,
        code_verifier=code_verifier,
    )

    if str(token_data.get("state") or "") != state_key:
        logger.warning("VK ID token response state mismatch")
        raise HTTPException(status_code=400, detail="Несовпадение state в ответе VK ID")

    vk_uid = token_data.get("user_id")
    if vk_uid is None and body.vk_redirect_user_id:
        vk_uid = body.vk_redirect_user_id.strip()
    vk_uid_str = str(vk_uid).strip() if vk_uid is not None else ""
    if not vk_uid_str:
        logger.warning("VK ID login: no user_id, keys=%s", list(token_data.keys()))
        raise HTTPException(status_code=400, detail="VK ID не вернул user_id")

    ui = await _vk_id_user_info(token_data["access_token"])
    user_block = ui.get("user") if isinstance(ui, dict) else None
    if not isinstance(user_block, dict):
        user_block = {}
    email = (user_block.get("email") or "").strip() or None

    identity = (
        db.query(models.UserOAuthIdentity)
        .filter(
            models.UserOAuthIdentity.provider == "vk",
            models.UserOAuthIdentity.provider_user_id == vk_uid_str,
        )
        .first()
    )
    if identity:
        user = db.query(models.User).filter(models.User.id == identity.user_id).first()
        if not user:
            raise HTTPException(status_code=500, detail="Пользователь не найден")
        return _issue_token_for_user(user)

    if email:
        user = _find_user_by_email_ci(db, email)
        if user:
            _attach_identity(db, user, "vk", vk_uid_str)
            user.email_verified = True
            db.add(user)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Не удалось привязать VK к аккаунту",
                )
            return _issue_token_for_user(user)

    if not email:
        email = _synthetic_email("vk", vk_uid_str)

    user = models.User(
        email=email,
        username=None,
        first_name=None,
        last_name=None,
        password_hash=security.get_password_hash(secrets.token_urlsafe(48)),
        role=models.UserRole.MANAGER,
        email_verified=True,
        email_verification_token_hash=None,
        email_verification_expires_at=None,
    )
    db.add(user)
    db.flush()
    db.add(
        models.UserOAuthIdentity(
            user_id=user.id,
            provider="vk",
            provider_user_id=vk_uid_str,
        )
    )
    SubscriptionService.ensure_default_subscription(db, user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Не удалось создать аккаунт: конфликт данных",
        )
    db.refresh(user)
    return _issue_token_for_user(user)
