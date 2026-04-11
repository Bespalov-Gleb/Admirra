"""
Вход и регистрация через Яндекс ID и VK ID (тот же OAuth client_id, что для интеграций рекламы).

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

VK_CLIENT_ID = cfg.oauth.vk_client_id
VK_ADS_TOKEN_URL = "https://ads.vk.com/api/v2/oauth2/token.json"
VK_ADS_AUTH_BASE = "https://ads.vk.com/hq/settings/access"
VK_ADS_OAUTH_SCOPE = cfg.oauth.vk_ads_oauth_scope

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


async def _vk_exchange_code(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": VK_CLIENT_ID,
            "redirect_uri": redirect_uri,
        }
        r = await client.post(VK_ADS_TOKEN_URL, data=payload, timeout=30.0)
        if r.status_code != 200:
            logger.warning("VK token exchange failed: %s %s", r.status_code, r.text[:300])
            raise HTTPException(status_code=400, detail="Не удалось обменять код VK на токен")
        return r.json()


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
    Тот же Authorization Code Grant, что для VK Ads API (VK ID).
    redirect_uri — callback (может совпадать с интеграцией: .../auth/vk/callback)
    """
    if not VK_CLIENT_ID:
        raise HTTPException(status_code=503, detail="VK OAuth не настроен на сервере")
    state = _sign_oauth_state("vk")
    enc_redirect = quote(redirect_uri, safe="")
    enc_scope = quote(VK_ADS_OAUTH_SCOPE, safe="")
    enc_state = quote(state, safe="")
    url = (
        f"{VK_ADS_AUTH_BASE}?action=oauth2&response_type=code&client_id={VK_CLIENT_ID}"
        f"&state={enc_state}&scope={enc_scope}&redirect_uri={enc_redirect}"
    )
    return {"url": url}


@router.post("/vk/callback", response_model=schemas.Token)
async def vk_oauth_callback(body: schemas.OAuthLoginCallbackRequest, db: Session = Depends(get_db)):
    _verify_oauth_state(body.state, "vk")
    token_data = await _vk_exchange_code(body.code.strip(), body.redirect_uri.strip())
    vk_uid = token_data.get("user_id")
    if vk_uid is None:
        raise HTTPException(status_code=400, detail="VK не вернул user_id в ответе токена")
    vk_uid_str = str(vk_uid).strip()

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
