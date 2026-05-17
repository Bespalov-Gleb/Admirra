import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

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
    logger.info("Registration attempt for email: %s", user.email)

    db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.username:
        db_user_name = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user_name:
            raise HTTPException(status_code=400, detail="Username already taken")

    hashed_password = security.get_password_hash(user.password)
    raw_token = generate_email_verification_raw_token()
    token_hash = hash_verification_token(raw_token)
    exp = verification_expiry(48)

    new_user = models.User(
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        password_hash=hashed_password,
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
        sent = await send_verification_link_email(user.email, verify_url)
        if not sent:
            raise HTTPException(status_code=503, detail="Failed to send verification email")
        return schemas.RegisterPendingResponse(email=user.email)

    if smtp_enabled() and not smtp_configured():
        logger.error("SMTP not configured; cannot send verification email to %s", user.email)
        raise HTTPException(
            status_code=503,
            detail="Email delivery is not configured on server",
        )

    logger.warning(
        "SMTP_ENABLED=false: registration OK for %s, verification email not sent",
        user.email,
    )
    return schemas.RegisterPendingResponse(
        email=user.email,
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
    user = db.query(models.User).filter(models.User.email == body.email).first()
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
    user = db.query(models.User).filter(models.User.email == login_data.email).first()

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

    if not AUTH_LOGIN_OTP_ENABLED:
        logger.info("AUTH_LOGIN_OTP_ENABLED=false, issuing JWT without OTP for %s", user.email)
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

    if not smtp_delivery_active():
        if smtp_enabled() and not smtp_configured():
            logger.error("SMTP not configured; cannot send login OTP")
            raise HTTPException(
                status_code=503,
                detail="Email delivery is not configured on server",
            )
        logger.warning("SMTP_ENABLED=false, issuing JWT without OTP for %s", user.email)
        log_history_event(
            db,
            actor=user,
            event_type="auth",
            action="login_succeeded",
            description="Успешный вход (fallback без OTP)",
            target_type="user",
            target_id=str(user.id),
        )
        token = _issue_login_session(db, user, request, response, remember_me=login_data.remember_me)
        db.commit()
        return token

    # Удаляем старые неиспользованные challenge этого пользователя
    db.query(models.LoginOtpChallenge).filter(
        models.LoginOtpChallenge.user_id == user.id,
        models.LoginOtpChallenge.consumed.is_(False),
    ).delete(synchronize_session=False)

    code = generate_otp_digits()
    ch_id = uuid.uuid4()
    challenge = models.LoginOtpChallenge(
        id=uuid.uuid4(),
        challenge_id=ch_id,
        user_id=user.id,
        otp_hash=hash_login_otp(code),
        expires_at=otp_expiry_minutes(10),
        attempts=0,
        consumed=False,
    )
    db.add(challenge)
    db.commit()

    sent = await send_login_otp_email(user.email, code)
    if not sent:
        raise HTTPException(status_code=503, detail="Failed to send login code")

    return schemas.LoginPasswordStepResponse(
        step="otp_required",
        challenge_id=ch_id,
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
    code = (body.code or "").strip()
    if len(code) != 6 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Invalid code format")

    ch = (
        db.query(models.LoginOtpChallenge)
        .filter(models.LoginOtpChallenge.challenge_id == body.challenge_id)
        .first()
    )
    if not ch or ch.consumed:
        raise HTTPException(status_code=401, detail="Invalid or expired challenge")

    exp = ch.expires_at
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < utcnow():
            raise HTTPException(status_code=401, detail="Challenge expired")

    if ch.attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    ch.attempts = ch.attempts + 1

    if not verify_login_otp(code, ch.otp_hash):
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid code")

    ch.consumed = True
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
    user = db.query(models.User).filter(models.User.email == body.email).first()
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
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    db.add(user)
    token = _issue_login_session(db, user, request, response, remember_me=False)
    db.commit()
    return token


@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user


def _update_user_settings(updates: schemas.UserUpdateSettings, current_user: models.User, db: Session):
    """Общая логика обновления настроек пользователя."""
    if updates.username is not None:
        existing = db.query(models.User).filter(
            models.User.username == updates.username,
            models.User.id != current_user.id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = updates.username
    if updates.first_name is not None:
        current_user.first_name = updates.first_name
    if updates.last_name is not None:
        current_user.last_name = updates.last_name
    if updates.yandex_finance_token is not None:
        current_user.yandex_finance_token = updates.yandex_finance_token
    if updates.report_telegram_chat_id is not None:
        current_user.report_telegram_chat_id = updates.report_telegram_chat_id
    if updates.report_max_chat_id is not None:
        current_user.report_max_chat_id = updates.report_max_chat_id
    if updates.report_max_user_id is not None:
        current_user.report_max_user_id = updates.report_max_user_id
    if updates.report_max_username is not None:
        current_user.report_max_username = updates.report_max_username
    if updates.report_delivery_channels is not None:
        import json

        allowed_channels = {"telegram", "max"}
        channels = [ch for ch in updates.report_delivery_channels if ch in allowed_channels]
        current_user.report_delivery_channels = json.dumps(channels) if channels else None
    if updates.report_email_recipients is not None:
        import json

        current_user.report_email_recipients = (
            json.dumps(updates.report_email_recipients) if updates.report_email_recipients else None
        )
    if updates.report_schedule is not None:
        current_user.report_schedule = updates.report_schedule
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


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
