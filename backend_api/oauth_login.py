"""
Вход и регистрация через Яндекс ID и VK.

- Яндекс: OAuth приложения Директа / login.
- VK: вход на сайт — Authorization Code Flow на oauth.vk.com (ключ пользователя ВКонтакте), без редиректа в кабинет VK Ads.
  Интеграция VK Ads по-прежнему использует ads.vk.com и VK_CLIENT_ID в backend_api/integrations.
  См. https://dev.vk.com/ru/api/access-token/authcode-flow-user

redirect_uri может совпадать с callback интеграций (/auth/yandex/callback, /auth/vk/callback):
фронт помечает вход в sessionStorage и после возврата вызывает эти эндпоинты, а не exchange интеграции.
"""

from __future__ import annotations

import logging
import secrets
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

# Вход: oauth.vk.com; при пустых VK_LOGIN_* используются VK_CLIENT_ID / VK_CLIENT_SECRET (одно приложение ВК).
VK_LOGIN_CLIENT_ID = (cfg.oauth.vk_login_client_id or cfg.oauth.vk_client_id or "").strip()
VK_LOGIN_CLIENT_SECRET = (cfg.oauth.vk_login_client_secret or cfg.oauth.vk_client_secret or "").strip()
VK_LOGIN_SCOPE = (cfg.oauth.vk_login_scope or "").strip()
VK_OAUTH_AUTHORIZE_URL = "https://oauth.vk.com/authorize"
VK_OAUTH_ACCESS_TOKEN_URL = "https://oauth.vk.com/access_token"
VK_OAUTH_API_VERSION = "5.199"

# Только профиль для входа в приложение (отдельно от direct:api при подключении Директа)
YANDEX_LOGIN_SCOPE = "login:email login:info"


def _sign_oauth_state(provider: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode(
        {"pur": "oauth_login", "prv": provider, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _verify_oauth_state(state: str, provider: str) -> None:
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")
    if payload.get("pur") != "oauth_login" or payload.get("prv") != provider:
        raise HTTPException(status_code=400, detail="Недействительный параметр state")


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


async def _vk_com_exchange_code(code: str, redirect_uri: str) -> dict:
    """Обмен code на данные пользователя (GET oauth.vk.com/access_token), не VK Ads API."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            VK_OAUTH_ACCESS_TOKEN_URL,
            params={
                "client_id": VK_LOGIN_CLIENT_ID,
                "client_secret": VK_LOGIN_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=30.0,
        )
        try:
            data = r.json()
        except Exception:
            logger.warning("VK oauth.vk.com token: non-JSON %s %s", r.status_code, r.text[:300])
            raise HTTPException(status_code=400, detail="Не удалось обменять код VK на токен")
        if data.get("error"):
            err = data.get("error_description") or data.get("error")
            logger.warning("VK oauth.vk.com error: %s", err)
            raise HTTPException(status_code=400, detail=str(err) if err else "Ошибка VK OAuth")
        if not data.get("access_token"):
            logger.warning("VK oauth.vk.com: no access_token, keys=%s", list(data.keys()))
            raise HTTPException(status_code=400, detail="VK не вернул access_token")
        return data


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
    Редирект на oauth.vk.com (Authorization Code Flow пользователя ВКонтакте).
    Не использует ads.vk.com — отдельно от подключения VK Ads в интеграциях.

    В кабинете приложения VK (vk.com/apps) укажите redirect_uri, например https://.../auth/vk/callback.
    Для входа без общего ключа с рекламой задайте VK_LOGIN_CLIENT_ID / VK_LOGIN_CLIENT_SECRET.
    """
    if not VK_LOGIN_CLIENT_ID or not VK_LOGIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Вход через VK: задайте VK_LOGIN_CLIENT_ID и VK_LOGIN_CLIENT_SECRET или VK_CLIENT_ID/VK_CLIENT_SECRET",
        )
    state = _sign_oauth_state("vk")
    q = [
        f"client_id={quote(VK_LOGIN_CLIENT_ID, safe='')}",
        "display=page",
        f"redirect_uri={quote(redirect_uri, safe='')}",
        "response_type=code",
        f"v={VK_OAUTH_API_VERSION}",
        f"state={quote(state, safe='')}",
    ]
    if VK_LOGIN_SCOPE:
        q.append(f"scope={quote(VK_LOGIN_SCOPE, safe='')}")
    url = f"{VK_OAUTH_AUTHORIZE_URL}?{'&'.join(q)}"
    return {"url": url}


@router.post("/vk/callback", response_model=schemas.Token)
async def vk_oauth_callback(body: schemas.OAuthLoginCallbackRequest, db: Session = Depends(get_db)):
    _verify_oauth_state(body.state, "vk")
    if not VK_LOGIN_CLIENT_ID or not VK_LOGIN_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="VK OAuth для входа не настроен на сервере")

    token_data = await _vk_com_exchange_code(body.code.strip(), body.redirect_uri.strip())

    vk_uid = token_data.get("user_id")
    if vk_uid is None and body.vk_redirect_user_id:
        vk_uid = body.vk_redirect_user_id.strip()
    vk_uid_str = str(vk_uid).strip() if vk_uid is not None else ""
    if not vk_uid_str:
        logger.warning(
            "VK oauth login: no user_id, keys=%s",
            list(token_data.keys()) if isinstance(token_data, dict) else type(token_data),
        )
        raise HTTPException(status_code=400, detail="VK не вернул user_id после обмена кода")

    email = (token_data.get("email") or "").strip() or None

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
