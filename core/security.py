from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core import models, schemas
from core.database import get_db
from core.config import get_config

# Configuration
cfg = get_config()
SECRET_KEY = cfg.security.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours
AUTH_REQUIRE_EMAIL_VERIFIED = cfg.auth.auth_require_email_verified
REFRESH_COOKIE_NAME = "admirra_refresh_token"
REFRESH_TOKEN_REMEMBER_DAYS = 30
REFRESH_TOKEN_SESSION_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _refresh_cookie_secure(request: Request) -> bool:
    host = (request.headers.get("host") or request.url.hostname or "").split(":")[0].lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        return True
    deploy_env = (cfg.public_domain.admierra_deploy_env or "").lower()
    return deploy_env in {"prod", "production"}


def set_refresh_cookie(response: Response, request: Request, token: str, remember_me: bool) -> None:
    max_age = REFRESH_TOKEN_REMEMBER_DAYS * 86400 if remember_me else REFRESH_TOKEN_SESSION_DAYS * 86400
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=_refresh_cookie_secure(request),
        samesite="lax",
        path="/api/auth",
    )


def clear_refresh_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=_refresh_cookie_secure(request),
        samesite="lax",
        path="/api/auth",
    )


def create_refresh_session(
    db: Session,
    user: models.User,
    request: Request,
    response: Response,
    remember_me: bool,
) -> None:
    raw_token = create_refresh_token()
    now = utcnow()
    ttl_days = REFRESH_TOKEN_REMEMBER_DAYS if remember_me else REFRESH_TOKEN_SESSION_DAYS
    session = models.AuthRefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=now + timedelta(days=ttl_days),
        remember_me=remember_me,
        user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        ip_address=(request.client.host if request.client else None),
        created_at=now,
        last_used_at=now,
    )
    db.add(session)
    set_refresh_cookie(response, request, raw_token, remember_me)


def revoke_refresh_session(db: Session, raw_token: Optional[str]) -> None:
    if not raw_token:
        return
    session = (
        db.query(models.AuthRefreshSession)
        .filter(models.AuthRefreshSession.token_hash == hash_refresh_token(raw_token))
        .first()
    )
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.add(session)


def consume_refresh_session(
    db: Session,
    raw_token: Optional[str],
    request: Request,
    response: Response,
    rotate: bool = False,
) -> Optional[models.User]:
    if not raw_token:
        return None
    now = utcnow()
    session = (
        db.query(models.AuthRefreshSession)
        .filter(models.AuthRefreshSession.token_hash == hash_refresh_token(raw_token))
        .first()
    )
    if (
        not session
        or session.revoked_at is not None
        or (_normalize_dt(session.expires_at) and _normalize_dt(session.expires_at) < now)
    ):
        return None

    user = db.query(models.User).filter(models.User.id == session.user_id).first()
    if not user or (AUTH_REQUIRE_EMAIL_VERIFIED and not getattr(user, "email_verified", True)):
        session.revoked_at = now
        db.add(session)
        return None

    session.last_used_at = now
    db.add(session)
    remember_me = bool(session.remember_me)
    if rotate:
        session.revoked_at = now
        create_refresh_session(db, user, request, response, remember_me=remember_me)
    else:
        set_refresh_cookie(response, request, raw_token, remember_me=remember_me)
    return user

# Encryption for sensitive tokens
ENCRYPTION_KEY = cfg.security.encryption_key
from cryptography.fernet import Fernet

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_token(token: str) -> str:
    if not token: return None
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token_encrypted: str) -> str:
    if not token_encrypted: return None
    return fernet.decrypt(token_encrypted.encode()).decode()

bearer_scheme = HTTPBearer()

def get_current_user(auth: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = auth.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    if AUTH_REQUIRE_EMAIL_VERIFIED and not getattr(user, "email_verified", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return user
