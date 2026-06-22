import asyncio
import logging
import os
import uuid
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from PIL import Image, ImageOps, UnidentifiedImageError

from core.database import get_db
from core import models, schemas, security
from core.public_domain import resolve_frontend_url
from .auth_helpers import (
    generate_email_verification_raw_token,
    generate_otp_digits,
    hash_login_otp,
    hash_verification_token,
    mask_email,
    otp_expiry_minutes,
    utcnow,
    verification_expiry,
    verify_login_otp,
)
from .services.auth_mail import (
    is_configured as smtp_configured,
    send_login_otp_email,
    send_reset_password_email,
    send_verification_link_email,
    send_welcome_email,
    smtp_delivery_active,
    smtp_enabled,
)
from .services.subscription import SubscriptionService
from .services.history import log_history_event
from core.config import get_config

logger = logging.getLogger("api")
router = APIRouter(prefix="/auth", tags=["Authentication"])

FRONTEND_URL = resolve_frontend_url()
cfg = get_config()
RESEND_COOLDOWN_SEC = cfg.auth.resend_cooldown_sec
AUTH_LOGIN_OTP_ENABLED = cfg.auth.auth_login_otp_enabled
AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_SIZE = (256, 256)
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads"))
USER_AVATAR_DIR = UPLOADS_DIR / "user-avatars"


def _user_avatar_public_url(filename: str) -> str:
    return f"/uploads/user-avatars/{filename}"


def _remove_user_avatar(avatar_url: str | None) -> None:
    if not avatar_url or not avatar_url.startswith("/uploads/user-avatars/"):
        return
    filename = avatar_url.rsplit("/", 1)[-1]
    if not filename:
        return
    try:
        (USER_AVATAR_DIR / filename).unlink(missing_ok=True)
    except OSError:
        pass


def _user_has_usable_password(user: models.User) -> bool:
    if getattr(user, "password_updated_at", None):
        return True
    identities = getattr(user, "oauth_identities", None) or []
    if identities:
        return False
    return bool(user.password_hash)


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _find_user_by_email_ci(db: Session, email: str) -> Optional[models.User]:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == normalized)
        .first()
    )


def _mask_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * max(len(value) - 4, 2)}{value[-2:]}"


def _decorate_user_response(resp: schemas.UserResponse, user: models.User) -> schemas.UserResponse:
    resp.has_password = _user_has_usable_password(user)
    return resp


def _create_otp_challenge(db: Session, user: models.User) -> tuple[models.LoginOtpChallenge, str]:
    db.query(models.LoginOtpChallenge).filter(
        models.LoginOtpChallenge.user_id == user.id,
        models.LoginOtpChallenge.consumed.is_(False),
    ).delete(synchronize_session=False)

    code = generate_otp_digits()
    challenge = models.LoginOtpChallenge(
        id=uuid.uuid4(),
        challenge_id=uuid.uuid4(),
        user_id=user.id,
        otp_hash=hash_login_otp(code),
        expires_at=otp_expiry_minutes(10),
        attempts=0,
        consumed=False,
    )
    db.add(challenge)
    db.commit()
    return challenge, code


def _verify_otp_challenge(
    db: Session,
    challenge_id: uuid.UUID,
    code: str,
    user_id: uuid.UUID | None = None,
) -> models.LoginOtpChallenge:
    normalized_code = (code or "").strip()
    if len(normalized_code) != 6 or not normalized_code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid code format")

    query = db.query(models.LoginOtpChallenge).filter(models.LoginOtpChallenge.challenge_id == challenge_id)
    if user_id is not None:
        query = query.filter(models.LoginOtpChallenge.user_id == user_id)
    ch = query.first()
    if not ch or ch.consumed:
        raise HTTPException(status_code=401, detail="Invalid or expired challenge")

    exp = ch.expires_at
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= utcnow():
            raise HTTPException(status_code=401, detail="Code expired")

    if ch.attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    if not verify_login_otp(normalized_code, ch.otp_hash):
        ch.attempts += 1
        db.add(ch)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid code")

    ch.consumed = True
    db.add(ch)
    return ch


def _issue_login_session(
    db: Session,
    user: models.User,
    request: Request,
    response: Response,
    remember_me: bool,
) -> dict:
    access_token = security.create_access_token(data={"sub": user.email})
    security.create_refresh_session(db, user, request, response, remember_me=remember_me)
    return {"access_token": access_token, "token_type": "bearer"}


def _activate_pending_team_invites(db: Session, user: models.User) -> None:
    pending = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.email == user.email,
            models.TeamMember.status == models.TeamMemberStatus.PENDING,
        )
        .all()
    )
    if not pending:
        return
    now = utcnow()
    for inv in pending:
        inv.user_id = user.id
        inv.status = models.TeamMemberStatus.ACTIVE
        inv.accepted_at = now
        db.add(inv)


def _frontend_verify_url(raw_token: str) -> str:
    return f"{FRONTEND_URL}/verify-email?token={raw_token}"


@router.post("/register", response_model=schemas.RegisterPendingResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация: пользователь создаётся с email_verified=False, JWT не выдаётся.
    На почту уходит ссылка с токеном.
    """
    email = _normalize_email(user.email)
    logger.info("Registration attempt for email: %s", email)

    db_user_email = _find_user_by_email_ci(db, email)
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # username — это отображаемое имя (с формы «Имя»), оно НЕ уникально и может
    # повторяться. Уникален только email. Поэтому дубль имени не проверяем.

    hashed_password = security.get_password_hash(user.password)
    raw_token = generate_email_verification_raw_token()
    token_hash = hash_verification_token(raw_token)
    exp = verification_expiry(48)

    new_user = models.User(
        email=email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hash=hashed_password,
        password_updated_at=utcnow(),
        role=models.UserRole.MANAGER,
        email_verified=False,
        email_verification_token_hash=token_hash,
        email_verification_expires_at=exp,
        verification_email_last_sent_at=utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    _activate_pending_team_invites(db, new_user)
    SubscriptionService.ensure_default_subscription(db, new_user)
    db.commit()

    verify_url = _frontend_verify_url(raw_token)
    if smtp_delivery_active():
        sent = await send_verification_link_email(email, verify_url)
        if not sent:
            raise HTTPException(status_code=503, detail="Failed to send verification email")
        return schemas.RegisterPendingResponse(email=email)

    if smtp_enabled() and not smtp_configured():
        logger.error("SMTP not configured; cannot send verification email to %s", email)
        raise HTTPException(
            status_code=503,
            detail="Email delivery is not configured on server",
        )

    logger.warning(
        "SMTP_ENABLED=false: registration OK for %s, verification email not sent",
        email,
    )
    return schemas.RegisterPendingResponse(
        email=email,
        message="Аккаунт создан. Отправка письма отключена (SMTP_ENABLED=false). "
        "Подтвердите email вручную или включите SMTP и используйте «Отправить снова».",
    )


@router.post("/verify-email", response_model=schemas.Token)
async def verify_email(
    body: schemas.VerifyEmailRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Подтверждение почты по одноразовому токену из ссылки — выдача JWT."""
    raw = (body.token or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Invalid token")

    th = hash_verification_token(raw)
    user = (
        db.query(models.User)
        .filter(
            models.User.email_verification_token_hash == th,
            models.User.email_verification_expires_at > utcnow(),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.add(user)

    if smtp_delivery_active():
        username = user.first_name or user.username or "Пользователь"
        await send_welcome_email(user.email, username)

    token = _issue_login_session(db, user, request, response, remember_me=False)
    db.commit()
    return token


@router.post("/resend-verification")
async def resend_verification(body: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    """Повторная отправка письма подтверждения (throttle)."""
    user = _find_user_by_email_ci(db, body.email)
    # Не раскрываем, есть ли пользователь
    generic = {"message": "Если email зарегистрирован и не подтверждён, письмо отправлено."}
    if not user or user.email_verified:
        return generic

    last = user.verification_email_last_sent_at
    if last:
        delta = (utcnow() - last).total_seconds()
        if delta < RESEND_COOLDOWN_SEC:
            raise HTTPException(
                status_code=429,
                detail=f"Повторная отправка возможна через {int(RESEND_COOLDOWN_SEC - delta)} с.",
            )

    raw_token = generate_email_verification_raw_token()
    user.email_verification_token_hash = hash_verification_token(raw_token)
    user.email_verification_expires_at = verification_expiry(48)
    user.verification_email_last_sent_at = utcnow()
    db.add(user)
    db.commit()

    if smtp_delivery_active():
        verify_url = _frontend_verify_url(raw_token)
        await send_verification_link_email(user.email, verify_url)
    elif smtp_enabled() and not smtp_configured():
        raise HTTPException(status_code=503, detail="Email delivery is not configured on server")
    return generic


@router.post("/login", response_model=schemas.LoginResponse)
async def login_password_step(
    login_data: schemas.UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Шаг 1 входа: проверка пароля.
    - Неподтверждённая почта → step=email_not_verified (без JWT), если AUTH_REQUIRE_EMAIL_VERIFIED.
    - Иначе → OTP на почту или JWT (как у подтверждённой почты).
    """
    user = _find_user_by_email_ci(db, login_data.email)

    if not user or not security.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _activate_pending_team_invites(db, user)
    db.commit()

    if security.AUTH_REQUIRE_EMAIL_VERIFIED and not user.email_verified:
        return schemas.LoginPasswordStepResponse(step="email_not_verified", email=user.email)

    otp_required = bool(getattr(user, "two_factor_enabled", False))

    if not otp_required:
        logger.info("2FA disabled for user, issuing JWT without OTP for %s", user.email)
        log_history_event(
            db,
            actor=user,
            event_type="auth",
            action="login_succeeded",
            description="Успешный вход (без OTP)",
            target_type="user",
            target_id=str(user.id),
        )
        token = _issue_login_session(db, user, request, response, remember_me=login_data.remember_me)
        db.commit()
        return token

    if not AUTH_LOGIN_OTP_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Двухфакторная аутентификация временно недоступна на сервере",
        )

    if not smtp_delivery_active():
        raise HTTPException(
            status_code=503,
            detail="Двухфакторная аутентификация временно недоступна: email-доставка не настроена",
        )

    challenge, code = _create_otp_challenge(db, user)

    sent = await send_login_otp_email(user.email, code)
    if not sent:
        raise HTTPException(status_code=503, detail="Failed to send login code")

    return schemas.LoginPasswordStepResponse(
        step="otp_required",
        challenge_id=challenge.challenge_id,
        email_masked=mask_email(user.email),
    )


@router.post("/login/verify", response_model=schemas.Token)
def login_verify_otp(
    body: schemas.LoginVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Шаг 2 входа: проверка OTP, выдача JWT."""
    ch = _verify_otp_challenge(db, body.challenge_id, body.code)
    user = db.query(models.User).filter(models.User.id == ch.user_id).first()
    if not user:
        db.commit()
        raise HTTPException(status_code=401, detail="User not found")

    log_history_event(
        db,
        actor=user,
        event_type="auth",
        action="login_succeeded",
        description="Успешный вход (OTP)",
        target_type="user",
        target_id=str(user.id),
    )
    token = _issue_login_session(db, user, request, response, remember_me=body.remember_me)
    db.commit()
    return token


@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """Silent refresh: validate httpOnly refresh cookie and rotate it."""
    raw_token = request.cookies.get(security.REFRESH_COOKIE_NAME)
    user = security.consume_refresh_session(db, raw_token, request, response)
    if not user:
        error_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Refresh session expired"},
        )
        security.clear_refresh_cookie(error_response, request)
        db.commit()
        return error_response
    db.commit()
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(security.REFRESH_COOKIE_NAME)
    security.revoke_refresh_session(db, raw_token)
    security.clear_refresh_cookie(response, request)
    db.commit()
    return {"message": "Logged out"}


@router.post("/reset-password/request", status_code=status.HTTP_200_OK)
async def reset_password_request(body: schemas.PasswordResetRequestBody, db: Session = Depends(get_db)):
    """Шаг 1 сброса пароля: отправляет ссылку на email (ответ всегда 200, чтобы не раскрывать наличие аккаунта)."""
    generic = {"message": "Если указанный email зарегистрирован, ссылка для сброса пароля отправлена."}
    user = _find_user_by_email_ci(db, body.email)
    if not user:
        return generic

    raw_token = generate_email_verification_raw_token()
    user.password_reset_token_hash = hash_verification_token(raw_token)
    user.password_reset_expires_at = verification_expiry(1)  # 1 час
    db.add(user)
    db.commit()

    if smtp_delivery_active():
        reset_url = f"{FRONTEND_URL}/reset-password/confirm?token={raw_token}"
        await send_reset_password_email(user.email, reset_url)
    return generic


@router.post("/reset-password/confirm", response_model=schemas.Token)
def reset_password_confirm(
    body: schemas.PasswordResetConfirmBody,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Шаг 2 сброса пароля: проверяет токен и обновляет пароль."""
    raw = (body.token or "").strip()
    if not raw or len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Неверный запрос")

    th = hash_verification_token(raw)
    user = (
        db.query(models.User)
        .filter(
            models.User.password_reset_token_hash == th,
            models.User.password_reset_expires_at > utcnow(),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=400, detail="Ссылка недействительна или срок действия истёк")

    user.password_hash = security.get_password_hash(body.new_password)
    user.password_updated_at = utcnow()
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    db.add(user)
    token = _issue_login_session(db, user, request, response, remember_me=False)
    db.commit()
    return token


@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    sub = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.user_id == current_user.id,
            models.Subscription.status.in_([
                models.SubscriptionStatus.ACTIVE,
                models.SubscriptionStatus.TRIAL,
            ]),
        )
        .order_by(models.Subscription.created_at.desc())
        .first()
    )
    wl = False
    if sub:
        if sub.plan_id:
            plan = db.query(models.TariffPlan).filter(models.TariffPlan.id == sub.plan_id).first()
            wl = bool(plan and getattr(plan, "whitelabel_included", False))
        if not wl:
            wl = SubscriptionService.get_user_plan(db, current_user).code == "standard"
    resp = schemas.UserResponse.model_validate(current_user)
    resp.whitelabel_available = wl
    return _decorate_user_response(resp, current_user)


@router.post("/metrika/identity", status_code=status.HTTP_204_NO_CONTENT)
def save_metrika_identity(
    body: schemas.MetrikaIdentityRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Сохранить ClientID Метрики и yclid на аккаунт (первое значение фиксируем —
    оно соответствует визиту, который привёл к регистрации). Для офлайн-конверсий."""
    changed = False
    cid = (body.client_id or "").strip()
    yclid = (body.yclid or "").strip()
    if cid and not current_user.metrika_client_id:
        current_user.metrika_client_id = cid[:128]
        changed = True
    if yclid and not current_user.metrika_yclid:
        current_user.metrika_yclid = yclid[:255]
        changed = True
    if changed:
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/metrika/milestone", response_model=schemas.MetrikaMilestoneResponse)
def claim_metrika_milestone(
    body: schemas.MetrikaMilestoneRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """Отметить достижение «вехи» Метрики единожды на аккаунт (дедуп «первого раза»,
    например integration_connected). first=True только при первом достижении."""
    import json as _json
    name = (body.name or "").strip()
    if not name:
        return schemas.MetrikaMilestoneResponse(first=False)
    try:
        claimed = set(_json.loads(current_user.ym_milestones)) if current_user.ym_milestones else set()
    except Exception:
        claimed = set()
    if name in claimed:
        return schemas.MetrikaMilestoneResponse(first=False)
    claimed.add(name)
    current_user.ym_milestones = _json.dumps(sorted(claimed))
    db.commit()
    return schemas.MetrikaMilestoneResponse(first=True)


def _update_user_settings(updates: schemas.UserUpdateSettings, current_user: models.User, db: Session):
    """Общая логика обновления настроек пользователя."""
    fields = updates.model_fields_set
    if "username" in fields:
        # username — отображаемое имя, может повторяться; дубль не проверяем.
        current_user.username = updates.username
    if "first_name" in fields:
        current_user.first_name = updates.first_name
    if "last_name" in fields:
        current_user.last_name = updates.last_name
    if "phone" in fields:
        current_user.phone = updates.phone
    if "notification_email" in fields:
        current_user.notification_email = str(updates.notification_email) if updates.notification_email else None
    if "interface_language" in fields:
        if updates.interface_language not in {"ru", "en"}:
            raise HTTPException(status_code=400, detail="Unsupported interface language")
        current_user.interface_language = updates.interface_language
    if "two_factor_enabled" in fields:
        next_two_factor = bool(updates.two_factor_enabled)
        if next_two_factor and not current_user.two_factor_enabled:
            raise HTTPException(
                status_code=400,
                detail="Подтвердите email-код, чтобы включить двухфакторную аутентификацию",
            )
        current_user.two_factor_enabled = next_two_factor
    if "global_detector_enabled" in fields:
        current_user.global_detector_enabled = bool(updates.global_detector_enabled)
    if "yandex_finance_token" in fields:
        current_user.yandex_finance_token = updates.yandex_finance_token
    if "report_telegram_chat_id" in fields:
        current_user.report_telegram_chat_id = updates.report_telegram_chat_id
    if "report_max_chat_id" in fields:
        current_user.report_max_chat_id = updates.report_max_chat_id
    if "report_max_user_id" in fields:
        current_user.report_max_user_id = updates.report_max_user_id
    if "report_max_username" in fields:
        current_user.report_max_username = updates.report_max_username
    if "report_delivery_channels" in fields:
        import json

        allowed_channels = {"telegram", "max", "email"}
        channels = [ch for ch in (updates.report_delivery_channels or []) if ch in allowed_channels]
        current_user.report_delivery_channels = json.dumps(channels)
    if "report_email_recipients" in fields:
        import json

        current_user.report_email_recipients = (
            json.dumps(updates.report_email_recipients) if updates.report_email_recipients else None
        )
    if "report_schedule" in fields:
        current_user.report_schedule = updates.report_schedule
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _decorate_user_response(schemas.UserResponse.model_validate(current_user), current_user)


@router.put("/me", response_model=schemas.UserResponse)
def update_users_me(
    updates: schemas.UserUpdateSettings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return _update_user_settings(updates, current_user, db)


@router.patch("/me", response_model=schemas.UserResponse)
def patch_users_me(
    updates: schemas.UserUpdateSettings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return _update_user_settings(updates, current_user, db)


@router.post("/me/2fa/start", response_model=schemas.LoginPasswordStepResponse)
async def start_users_me_two_factor(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if current_user.two_factor_enabled:
        return schemas.LoginPasswordStepResponse(step="otp_required", email_masked=mask_email(current_user.email))
    if not _user_has_usable_password(current_user):
        raise HTTPException(status_code=400, detail="Сначала задайте пароль для аккаунта")
    if not AUTH_LOGIN_OTP_ENABLED:
        raise HTTPException(status_code=503, detail="Двухфакторная аутентификация отключена на сервере")
    if not smtp_delivery_active():
        raise HTTPException(status_code=503, detail="Email-доставка не настроена на сервере")

    challenge, code = _create_otp_challenge(db, current_user)
    sent = await send_login_otp_email(current_user.email, code)
    if not sent:
        raise HTTPException(status_code=503, detail="Не удалось отправить код")
    return schemas.LoginPasswordStepResponse(
        step="otp_required",
        challenge_id=challenge.challenge_id,
        email_masked=mask_email(current_user.email),
    )


@router.post("/me/2fa/verify", response_model=schemas.UserResponse)
def verify_users_me_two_factor(
    body: schemas.TwoFactorSetupVerifyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    _verify_otp_challenge(db, body.challenge_id, body.code, user_id=current_user.id)
    current_user.two_factor_enabled = True
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _decorate_user_response(schemas.UserResponse.model_validate(current_user), current_user)


@router.post("/me/avatar", response_model=schemas.UserResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Поддерживаются PNG, JPG и WebP")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Файл пустой")
    if len(raw) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Файл больше 5 МБ")
    try:
        image = Image.open(BytesIO(raw))
        image = ImageOps.exif_transpose(image).convert("RGBA")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Не удалось прочитать изображение")

    image.thumbnail(AVATAR_SIZE)
    canvas = Image.new("RGBA", AVATAR_SIZE, (255, 255, 255, 0))
    canvas.alpha_composite(image, ((AVATAR_SIZE[0] - image.width) // 2, (AVATAR_SIZE[1] - image.height) // 2))
    USER_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}-{uuid.uuid4().hex}.png"
    canvas.save(USER_AVATAR_DIR / filename, format="PNG", optimize=True)
    _remove_user_avatar(current_user.avatar_url)
    current_user.avatar_url = _user_avatar_public_url(filename)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _decorate_user_response(schemas.UserResponse.model_validate(current_user), current_user)


@router.delete("/me/avatar", response_model=schemas.UserResponse)
def delete_user_avatar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    _remove_user_avatar(current_user.avatar_url)
    current_user.avatar_url = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _decorate_user_response(schemas.UserResponse.model_validate(current_user), current_user)


@router.post("/me/password", response_model=schemas.UserResponse)
def change_users_me_password(
    body: schemas.PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    new_password = (body.new_password or "").strip()
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 8 символов")
    if _user_has_usable_password(current_user):
        if not body.current_password or not security.verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")
    current_user.password_hash = security.get_password_hash(new_password)
    current_user.password_updated_at = utcnow()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _decorate_user_response(schemas.UserResponse.model_validate(current_user), current_user)


@router.get("/me/oauth-identities", response_model=list[schemas.OAuthIdentityStatus])
def get_users_me_oauth_identities(
    current_user: models.User = Depends(security.get_current_user),
):
    connected = {identity.provider for identity in (current_user.oauth_identities or [])}
    has_password = _user_has_usable_password(current_user)
    connected_count = len(connected)
    providers = [
        {
            "provider": "yandex",
            "label": "Яндекс ID",
            "short": "Я",
            "icon_url": "/admirra/img/icons/yandex.png",
        },
        {
            "provider": "vk",
            "label": "ВКонтакте",
            "short": "VK",
            "icon_url": "/admirra/img/icons/vk.png",
        },
        {
            "provider": "max",
            "label": "Max",
            "short": "M",
            "icon_url": "/admirra/img/icons/max.png",
        },
    ]
    result = []
    for item in providers:
        provider = item["provider"]
        is_connected = provider in connected
        can_unlink = bool(is_connected and (has_password or connected_count > 1))
        hint = None
        if is_connected and not can_unlink:
            hint = "Сначала задайте пароль или привяжите другой способ входа."
        result.append(
            schemas.OAuthIdentityStatus(
                provider=provider,
                label=item["label"],
                short=item["short"],
                icon_url=item["icon_url"],
                connected=is_connected,
                can_unlink=can_unlink,
                hint=hint,
            )
        )
    return result


@router.delete("/me/oauth-identities/{provider}", response_model=list[schemas.OAuthIdentityStatus])
def unlink_users_me_oauth_identity(
    provider: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    provider = provider.lower()
    if provider not in {"yandex", "vk", "max"}:
        raise HTTPException(status_code=404, detail="Провайдер не найден")
    identity = next((item for item in (current_user.oauth_identities or []) if item.provider == provider), None)
    if not identity:
        raise HTTPException(status_code=404, detail="Способ входа не привязан")
    connected_count = len(current_user.oauth_identities or [])
    if not _user_has_usable_password(current_user) and connected_count <= 1:
        raise HTTPException(status_code=400, detail="Сначала задайте пароль или привяжите другой способ входа")
    db.delete(identity)
    db.commit()
    db.refresh(current_user)
    return get_users_me_oauth_identities(current_user)


def _ids(rows):
    return [row[0] for row in rows]


def _delete_user_account_data(db: Session, user_id: uuid.UUID) -> None:
    client_ids = _ids(db.query(models.Client.id).filter(models.Client.owner_id == user_id).all())
    phone_project_ids = _ids(db.query(models.PhoneProject.id).filter(models.PhoneProject.owner_id == user_id).all())
    team_member_ids = _ids(db.query(models.TeamMember.id).filter(models.TeamMember.account_id == user_id).all())

    if phone_project_ids:
        db.query(models.Lead).filter(models.Lead.project_id.in_(phone_project_ids)).delete(synchronize_session=False)
        db.query(models.PhoneProject).filter(models.PhoneProject.id.in_(phone_project_ids)).delete(synchronize_session=False)

    if team_member_ids:
        db.query(models.TeamMemberProject).filter(
            models.TeamMemberProject.team_member_id.in_(team_member_ids)
        ).delete(synchronize_session=False)
        db.query(models.TeamMember).filter(models.TeamMember.id.in_(team_member_ids)).delete(synchronize_session=False)
    db.query(models.TeamMember).filter(models.TeamMember.user_id == user_id).update(
        {models.TeamMember.user_id: None},
        synchronize_session=False,
    )

    db.query(models.HistoryEvent).filter(models.HistoryEvent.actor_user_id == user_id).update(
        {models.HistoryEvent.actor_user_id: None},
        synchronize_session=False,
    )
    db.query(models.HistoryEvent).filter(models.HistoryEvent.account_id == user_id).delete(synchronize_session=False)

    if client_ids:
        integration_ids = _ids(
            db.query(models.Integration.id).filter(models.Integration.client_id.in_(client_ids)).all()
        )
        direction_ids = _ids(
            db.query(models.ProjectDirection.id).filter(models.ProjectDirection.client_id.in_(client_ids)).all()
        )

        db.query(models.HistoryEvent).filter(models.HistoryEvent.client_id.in_(client_ids)).update(
            {models.HistoryEvent.client_id: None},
            synchronize_session=False,
        )
        db.query(models.PhoneProject).filter(models.PhoneProject.client_id.in_(client_ids)).update(
            {models.PhoneProject.client_id: None},
            synchronize_session=False,
        )
        db.query(models.TeamMemberProject).filter(
            models.TeamMemberProject.project_id.in_(client_ids)
        ).delete(synchronize_session=False)
        db.query(models.DetectorAlert).filter(models.DetectorAlert.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.ProjectBudget).filter(models.ProjectBudget.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.ProjectTargetCPA).filter(models.ProjectTargetCPA.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.MetrikaGoals).filter(models.MetrikaGoals.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.WeeklyReport).filter(models.WeeklyReport.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.MonthlyReport).filter(models.MonthlyReport.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.YandexStats).filter(models.YandexStats.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.YandexKeywords).filter(models.YandexKeywords.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.YandexGroups).filter(models.YandexGroups.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.YandexAds).filter(models.YandexAds.client_id.in_(client_ids)).delete(
            synchronize_session=False
        )
        db.query(models.VKStats).filter(models.VKStats.client_id.in_(client_ids)).delete(synchronize_session=False)

        if direction_ids:
            db.query(models.ProjectDirectionMask).filter(
                models.ProjectDirectionMask.direction_id.in_(direction_ids)
            ).delete(synchronize_session=False)
            db.query(models.ProjectDirection).filter(models.ProjectDirection.id.in_(direction_ids)).delete(
                synchronize_session=False
            )

        if integration_ids:
            db.query(models.SyncJob).filter(models.SyncJob.integration_id.in_(integration_ids)).delete(
                synchronize_session=False
            )
            db.query(models.Campaign).filter(models.Campaign.integration_id.in_(integration_ids)).delete(
                synchronize_session=False
            )
            db.query(models.Integration).filter(models.Integration.id.in_(integration_ids)).delete(
                synchronize_session=False
            )

        db.query(models.Client).filter(models.Client.id.in_(client_ids)).delete(synchronize_session=False)

    db.query(models.DetectorAlert).filter(models.DetectorAlert.owner_id == user_id).delete(synchronize_session=False)
    db.query(models.MaxOAuthLoginAttempt).filter(models.MaxOAuthLoginAttempt.user_id == user_id).update(
        {models.MaxOAuthLoginAttempt.user_id: None},
        synchronize_session=False,
    )
    db.query(models.LoginOtpChallenge).filter(models.LoginOtpChallenge.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.AuthRefreshSession).filter(models.AuthRefreshSession.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.TelegramLinkToken).filter(models.TelegramLinkToken.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.MaxReportLinkToken).filter(models.MaxReportLinkToken.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.UserOAuthIdentity).filter(models.UserOAuthIdentity.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.Subscription).filter(models.Subscription.user_id == user_id).delete(synchronize_session=False)
    db.query(models.Notification).filter(models.Notification.user_id == user_id).delete(synchronize_session=False)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_users_me(
    confirmation: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if confirmation != "УДАЛИТЬ":
        raise HTTPException(status_code=400, detail="Введите УДАЛИТЬ для подтверждения")
    _remove_user_avatar(current_user.avatar_url)
    _delete_user_account_data(db, current_user.id)
    db.delete(current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
