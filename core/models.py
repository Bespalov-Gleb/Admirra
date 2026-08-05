import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer, Numeric, Date, Enum, BigInteger, Boolean, UniqueConstraint, JSON, Sequence, LargeBinary, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class UserRole(enum.Enum):
    ADMIN = "ADMIN"  # legacy → superadmin
    SUPERADMIN = "SUPERADMIN"
    MANAGER = "MANAGER"  # клиент SaaS
    STAFF_MANAGER = "STAFF_MANAGER"  # внутренний менеджер (панель /api/manager)
    SUPPORT = "SUPPORT"  # legacy, те же права что STAFF_MANAGER
    SEO = "SEO"
    DEVELOPER = "DEVELOPER"


class StaffStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"

class ClientStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"

class TeamMemberRole(enum.Enum):
    MEMBER = "member"
    CLIENT = "client"

class TeamMemberStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, index=True, nullable=True)  # отображаемое имя, НЕ уникально (логин — по email)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    password_updated_at = Column(DateTime(timezone=True), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.MANAGER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    interface_language = Column(String(8), nullable=False, default="ru")
    global_detector_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    # Пользовательский FinanceToken для Яндекс.Директа (или его база)
    # Используется при запросе баланса через AccountManagement API.
    yandex_finance_token = Column(String, nullable=True)
    # Avito Ads credentials (encrypted)
    avito_credential_type = Column(String(32), nullable=True)
    avito_api_key = Column(String, nullable=True)
    avito_client_id = Column(String, nullable=True)
    avito_client_secret = Column(String, nullable=True)
    # Настройки доставки отчётов
    report_telegram_chat_id = Column(String, nullable=True)
    report_max_chat_id = Column(String, nullable=True)
    report_max_user_id = Column(String, nullable=True)
    report_max_username = Column(String, nullable=True)
    report_delivery_channels = Column(String, nullable=True)  # JSON массив: telegram, max
    report_email_recipients = Column(String, nullable=True)  # JSON массив email адресов
    notification_email = Column(String, nullable=True)
    report_schedule = Column(String, nullable=True)  # JSON: {"day":"daily","time":"10:00"}

    # Подтверждение email (регистрация)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token_hash = Column(String, nullable=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    verification_email_last_sent_at = Column(DateTime(timezone=True), nullable=True)
    # Сброс пароля
    password_reset_token_hash = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)

    is_subscribed = Column(Boolean, nullable=False, default=False)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    ai_requests_used = Column(Integer, nullable=False, default=0)
    ai_requests_period_started_at = Column(DateTime(timezone=True), nullable=True)
    # Поля админ-панели (internal_admin): последний вход, UTM регистрации,
    # причина блокировки, сброс AI-квоты, staff-статус и 2FA сотрудника.
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    registration_utm_source = Column(String, nullable=True)
    registration_utm_medium = Column(String, nullable=True)
    registration_utm_campaign = Column(String, nullable=True)
    block_reason = Column(String, nullable=True)
    ai_quota_resets_at = Column(DateTime(timezone=True), nullable=True)
    staff_status = Column(Enum(StaffStatus), nullable=True)
    staff_totp_enabled = Column(Boolean, nullable=False, default=False)
    staff_totp_secret_encrypted = Column(String, nullable=True)
    staff_totp_pending_secret_encrypted = Column(String, nullable=True)
    staff_recovery_codes_hashed = Column(JSON, nullable=True)

    brand_logo_url = Column(String, nullable=True)
    brand_color = Column(String(7), nullable=True)
    brand_pdf_header = Column(String, nullable=True)
    brand_pdf_signature = Column(String, nullable=True)
    brand_custom_domain = Column(String, nullable=True)
    brand_domain_status = Column(String(16), nullable=True, default="none")

    # Яндекс.Метрика: идентификаторы для серверных офлайн-конверсий (счётчик 109911357).
    # Собираются на фронте при регистрации/входе и привязываются к аккаунту.
    metrika_client_id = Column(String, nullable=True)
    metrika_yclid = Column(String, nullable=True)
    # Достигнутые «вехи» Метрики (JSON-список), для дедупликации целей «первого
    # раза» (integration_connected и т.п.) на стороне сервера.
    ym_milestones = Column(Text, nullable=True)

    clients = relationship("Client", back_populates="owner")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    oauth_identities = relationship(
        "UserOAuthIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    team_memberships = relationship(
        "TeamMember",
        foreign_keys="TeamMember.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owned_team_members = relationship(
        "TeamMember",
        foreign_keys="TeamMember.account_id",
        back_populates="account",
        cascade="all, delete-orphan",
    )


class LoginOtpChallenge(Base):
    """Временный второй фактор входа: код на email (после успешного пароля)."""
    __tablename__ = "login_otp_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otp_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)


class AuthRefreshSession(Base):
    """Long-lived browser session backed by an httpOnly refresh-token cookie."""
    __tablename__ = "auth_refresh_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    remember_me = Column(Boolean, default=False, nullable=False)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="auth_refresh_sessions")


class MaxOAuthLoginAttempt(Base):
    """One-time MAX bot login attempt: website state + bot deeplink payload."""

    __tablename__ = "max_oauth_login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_hash = Column(String(128), unique=True, nullable=False, index=True)
    payload_hash = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    max_user_id = Column(String(128), nullable=True, index=True)
    max_username = Column(String(255), nullable=True)
    max_name = Column(String(255), nullable=True)
    max_chat_id = Column(String(128), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="max_oauth_login_attempts")


class YandexIntegrationOAuthAttempt(Base):
    """One-time OAuth session for connecting Yandex Direct or Metrika.

    The browser receives only a high-entropy ``state`` value.  The project,
    requested platform and the Avito resume context remain server-side, so a
    stale browser storage entry can never attach a token to another project.
    """

    __tablename__ = "yandex_integration_oauth_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_hash = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    client_name = Column(String(255), nullable=True)
    platform = Column(String(32), nullable=False)
    flow = Column(String(32), nullable=False, default="yandex_direct", server_default="yandex_direct")
    resume_integration_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    redirect_uri = Column(String(2048), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="yandex_integration_oauth_attempts")
    client = relationship("Client", backref="yandex_integration_oauth_attempts")


class TelegramLinkToken(Base):
    """
    Одноразовый токен для deep link t.me/<bot>?start=<token>.
    После /start в Telegram webhook привязывает chat_id к пользователю.
    """

    __tablename__ = "telegram_link_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type = Column(String(24), nullable=True)  # group | client; NULL = personal account binding
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="telegram_link_tokens")


class MaxReportLinkToken(Base):
    """
    Одноразовый токен для deep link max.ru/<bot>?start=<token>.
    После bot_started webhook привязывает MAX-чат к пользователю для отчётов.
    """

    __tablename__ = "max_report_link_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type = Column(String(24), nullable=True)  # group | client; NULL = personal account binding
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="max_report_link_tokens")


class UserOAuthIdentity(Base):
    """
    Привязка аккаунта приложения к Яндекс ID / VK ID / MAX ID.
    Не путать с токенами интеграций рекламных кабинетов.
    """

    __tablename__ = "user_oauth_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)  # yandex | vk | max
    provider_user_id = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="oauth_identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_uid"),
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
    )


class ReportSchedule(Base):
    """Единственная настройка автоотправки для конкретного проекта/папки."""
    __tablename__ = "report_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    # Скоуп данных: NULL+NULL = все проекты; client_id = проект; folder_id = папка
    scope_client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True)
    scope_folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    platform = Column(String, nullable=False, default="all", server_default="all")  # all|yandex|vk|avito
    channels = Column(String, nullable=False, default="[]")  # JSON: ["telegram","max","email"]
    email_recipients = Column(String, nullable=False, default="[]", server_default="[]")
    day = Column(String, nullable=False, default="daily", server_default="daily")  # daily|weekdays|monday..sunday
    send_time = Column(String, nullable=False, default="10:00", server_default="10:00")  # HH:MM МСК
    period_days = Column(Integer, nullable=False, default=7, server_default="7")  # период данных отчёта
    report_format = Column(String, nullable=False, default="desktop", server_default="desktop")  # desktop|mobile
    include_dynamics = Column(Boolean, nullable=False, default=False, server_default="false")
    approval_required = Column(Boolean, nullable=False, default=True, server_default="true")
    include_ai_comment = Column(Boolean, nullable=False, default=True, server_default="true")
    # Состав отчёта: JSON-список секций (kpi|chart|channels|campaigns)
    sections = Column(String, nullable=True)
    # Метрики графиков: JSON-списки (cost|impressions|clicks|cpc|cpa|leads) — на каждую
    # выбранную метрику рендерится отдельный график (столбиком, со своими осями)
    chart_metrics = Column(String, nullable=True)
    dynamics_metrics = Column(String, nullable=True)
    # Дополнительные цели доставки: JSON-список UUID групп (ReportChatTarget)
    chat_targets = Column(String, nullable=True)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="report_schedules")

    __table_args__ = (
        Index("ix_report_schedules_due_lookup", "enabled", "send_time", "day"),
        Index("uq_report_schedules_project_scope", "user_id", "scope_client_id", unique=True, postgresql_where=text("scope_client_id IS NOT NULL AND scope_folder_id IS NULL")),
        Index("uq_report_schedules_folder_scope", "user_id", "scope_folder_id", unique=True, postgresql_where=text("scope_folder_id IS NOT NULL AND scope_client_id IS NULL")),
    )


class ReportDelivery(Base):
    """Снимок/задание отправки отчёта.

    Используется для очереди «ждёт проверки» и истории доставок. Сам файл отчёта
    не хранится в БД: при утверждении он генерируется по зафиксированным
    параметрам периода, проекта/папки и состава.
    """
    __tablename__ = "report_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("report_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(24), nullable=False, default="pending", server_default="pending", index=True)
    source = Column(String(24), nullable=False, default="manual", server_default="manual")  # manual|auto|detector
    platform = Column(String, nullable=False, default="all", server_default="all")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    channels = Column(String, nullable=False, default="[]", server_default="[]")
    email_recipients = Column(String, nullable=False, default="[]", server_default="[]")
    chat_targets = Column(String, nullable=True)
    report_format = Column(String, nullable=False, default="desktop", server_default="desktop")
    include_dynamics = Column(Boolean, nullable=False, default=False, server_default="false")
    include_ai_comment = Column(Boolean, nullable=False, default=True, server_default="true")
    sections = Column(String, nullable=True)
    chart_metrics = Column(String, nullable=True)
    dynamics_metrics = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    # none | draft | edited | approved.  Stored server-side so the preview keeps
    # the correct state after a refresh instead of inventing it in the browser.
    comment_status = Column(String(16), nullable=False, default="none", server_default="none")
    anomaly_reason = Column(Text, nullable=True)
    delivery_results = Column(JSON, nullable=True)
    # Неизменяемый снимок: превью и все каналы используют одни и те же цифры/файлы.
    snapshot_data = Column(JSON, nullable=True)
    pdf_snapshot = Column(LargeBinary, nullable=True)
    png_snapshot = Column(LargeBinary, nullable=True)
    public_token = Column(String(64), nullable=True, unique=True, index=True)
    public_expires_at = Column(DateTime(timezone=True), nullable=True)
    snapshot_created_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], backref="report_deliveries")
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    schedule = relationship("ReportSchedule", backref="deliveries")

    __table_args__ = (
        Index(
            "uq_report_deliveries_schedule_period",
            "schedule_id", "start_date", "end_date",
            unique=True,
            postgresql_where=text("schedule_id IS NOT NULL"),
        ),
    )


class ReportChatTarget(Base):
    """Групповой чат (Telegram/MAX), куда пользователь подключил бота для отчётов.
    Привязка: пользователь получает код, добавляет бота в группу и отправляет там
    команду /link <код> — webhook сохраняет chat_id группы."""
    __tablename__ = "report_chat_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)
    target_type = Column(String(24), nullable=False, default="group", server_default="group")  # group | client
    kind = Column(String, nullable=False)  # telegram | max
    chat_id = Column(String, nullable=False)
    title = Column(String, nullable=True)
    # A linked chat is active until a delivery to this exact recipient fails.
    # The next successful retry restores it automatically.
    status = Column(String(24), nullable=False, default="active", server_default="active")
    last_error = Column(Text, nullable=True)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="report_chat_targets")


class ReportEmailRecipient(Base):
    """Адрес получателя отчётов, привязанный к одному проекту или папке.

    Старые массивы email в расписаниях остаются как список выбранных адресов,
    а эта таблица даёт адресам собственный статус и историю ошибки.  Благодаря
    этому можно отключить и повторить доставку только одному email.
    """
    __tablename__ = "report_email_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)
    email = Column(String(320), nullable=False)
    title = Column(String(255), nullable=True)
    status = Column(String(24), nullable=False, default="active", server_default="active")
    last_error = Column(Text, nullable=True)
    last_delivery_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Не `report_email_recipients`: это имя уже занято legacy JSON-полем User
    # с выбранными адресами личной доставки. Разделяем хранимый список и ORM-строки.
    user = relationship("User", backref="report_email_recipient_records")

    __table_args__ = (
        UniqueConstraint("user_id", "client_id", "folder_id", "email", name="uq_report_email_recipient_scope"),
    )


class Folder(Base):
    """Папка проектов: контейнер над проектами для сети филиалов одного заказчика.
    Сводка папки не хранится — считается на чтение как агрегат по вложенным проектам.
    Один уровень вложенности (папка в папке не поддерживается)."""
    __tablename__ = "folders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    color = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    clients = relationship("Client", back_populates="folder")


clients_display_id_seq = Sequence("clients_display_id_seq", start=100001)


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_id = Column(
        Integer,
        clients_display_id_seq,
        unique=True,
        nullable=False,
        server_default=clients_display_id_seq.next_value(),
    )
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String, nullable=False)
    description = Column(String)
    spreadsheet_id = Column(String)
    avatar_url = Column(String)
    site_url = Column(String, nullable=True)
    direction_label = Column(String(32), nullable=False, default="directions", server_default="directions")
    # AI-комментарий (промпт v1, правило 10): режим бюджета направлений —
    # fixed запрещает рекомендовать перелив, flexible разрешает.
    directions_budget_mode = Column(String(16), nullable=False, default="fixed", server_default="fixed")
    # AI-комментарий (правило 13): заявленная стратегия периода — свободный
    # текст менеджера; изменения по стратегии не считаются аномалией.
    strategy_context = Column(Text, nullable=True)
    status = Column(Enum(ClientStatus), default=ClientStatus.ACTIVE, nullable=False, server_default="ACTIVE")
    detector_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    detector_onboarding_dismissed_until = Column(DateTime(timezone=True), nullable=True)
    actual_start_date = Column(Date, nullable=True)
    # Проект лежит максимум в одной папке; NULL = корень списка (как раньше)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_ai_comment = Column(Text, nullable=True)
    last_ai_comment_at = Column(DateTime, nullable=True)
    # Кэш AI-комментариев по стандартным периодам (ТЗ §12, раздел 6):
    # {period_key: {"text": str, "generated_at": iso, "start": date, "end": date}}
    ai_comment_cache = Column(JSON, nullable=True)
    # §9.2 экономики: модель «тёплых» проектов. last_dashboard_viewed_at пишется
    # при открытии дашборда любым пользователем аккаунта — по нему проект считается
    # «тёплым» (окно warm_window_days) и от него же берётся дельта «с последнего
    # захода» (§9.5). last_comment_generated_at — троттлинг ночной генерации.
    last_dashboard_viewed_at = Column(DateTime(timezone=True), nullable=True)
    last_comment_generated_at = Column(DateTime(timezone=True), nullable=True)
    # Снимок KPI на момент предыдущего открытия — настоящая дельта since_last_visit.
    last_dashboard_snapshot = Column(JSON, nullable=True)
    # Короткая память проекта: anomaly -> action -> outcome.
    ai_comment_memory = Column(JSON, nullable=True)

    owner = relationship("User", back_populates="clients")
    folder = relationship("Folder", back_populates="clients")
    integrations = relationship("Integration", back_populates="client")
    directions = relationship("ProjectDirection", back_populates="client", cascade="all, delete-orphan")
    budgets = relationship("ProjectBudget", back_populates="client", cascade="all, delete-orphan")
    target_cpas = relationship("ProjectTargetCPA", back_populates="client", cascade="all, delete-orphan")
    yandex_stats = relationship("YandexStats", back_populates="client")
    yandex_keywords = relationship("YandexKeywords", back_populates="client")
    yandex_groups = relationship("YandexGroups", back_populates="client")
    yandex_ads = relationship("YandexAds", back_populates="client")
    vk_stats = relationship("VKStats", back_populates="client")
    avito_stats = relationship("AvitoStats", back_populates="client")
    avito_groups = relationship("AvitoGroups", back_populates="client")
    avito_creatives = relationship("AvitoCreatives", back_populates="client")
    weekly_reports = relationship("WeeklyReport", back_populates="client")
    monthly_reports = relationship("MonthlyReport", back_populates="client")
    team_accesses = relationship("TeamMemberProject", back_populates="project", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String, nullable=False, index=True)
    role = Column(Enum(TeamMemberRole), nullable=False, default=TeamMemberRole.MEMBER)
    status = Column(Enum(TeamMemberStatus), nullable=False, default=TeamMemberStatus.PENDING)
    invited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    account = relationship("User", foreign_keys=[account_id], back_populates="owned_team_members")
    user = relationship("User", foreign_keys=[user_id], back_populates="team_memberships")
    projects = relationship("TeamMemberProject", back_populates="team_member", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("account_id", "email", name="uq_team_member_account_email"),
    )


class TeamMemberProject(Base):
    __tablename__ = "team_member_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_member_id = Column(UUID(as_uuid=True), ForeignKey("team_members.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    team_member = relationship("TeamMember", back_populates="projects")
    project = relationship("Client", back_populates="team_accesses")

    __table_args__ = (
        UniqueConstraint("team_member_id", "project_id", name="uq_team_member_project"),
    )

class IntegrationPlatform(enum.Enum):
    YANDEX_DIRECT = "YANDEX_DIRECT"
    VK_ADS = "VK_ADS"
    YANDEX_METRIKA = "YANDEX_METRIKA"
    MYTARGET = "MYTARGET"
    AVITO_ADS = "AVITO_ADS"

class IntegrationSyncStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    NEVER = "NEVER"


class SyncJobStatus(enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SubscriptionStatus(enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"

class Integration(Base):
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    platform = Column(Enum(IntegrationPlatform), nullable=False)
    # Pending VK client-link integrations are deliberately created before OAuth,
    # therefore an access token appears only after the client authorizes it.
    access_token = Column(String, nullable=True) # Should be encrypted in production
    refresh_token = Column(String)
    platform_client_id = Column(String) # For platforms like VK Ads
    platform_client_secret = Column(String) # For platforms like VK Ads
    expires_at = Column(DateTime)
    account_id = Column(String) # Logic ID in the platform
    account_name = Column(String, nullable=True) # Human-readable cabinet/cabinet name (e.g. Yandex ClientInfo)
    vk_user_id = Column(String, nullable=True) # VK Ads user_id for token revocation (optional)
    sync_status = Column(Enum(IntegrationSyncStatus), default=IntegrationSyncStatus.NEVER)
    last_sync_at = Column(DateTime)
    # 'auto' — последний синк выполнен ночным планировщиком; 'manual' — пользователем; NULL — неизвестно/старые записи
    last_sync_trigger = Column(String(16), nullable=True)
    error_message = Column(String)
    
    # Sync settings
    auto_sync = Column(Boolean, default=True)
    sync_interval = Column(Integer, default=1440) # In minutes, default 24h
    
    # Agency Mode Support
    is_agency = Column(Boolean, default=False)
    agency_client_login = Column(String, nullable=True) # Logic login of the sub-client for Agency tokens

    # Каким OAuth-приложением Яндекса выдан токен: NULL — основное,
    # 'org' — «AdMirra — для организаций» (вход как сотрудник организации).
    # Нужен, чтобы refresh шёл через client_id/secret того же приложения.
    oauth_app = Column(String(16), nullable=True)

    # Goals Support
    selected_goals = Column(String, nullable=True) # JSON list of goal IDs
    primary_goal_id = Column(String, nullable=True)
    # VK Ads: explicitly selected objective/result types that count as leads.
    # Kept separate from selected_goals, which belongs to Metrika integrations.
    lead_action_types = Column(String, nullable=True) # JSON list of VK objective codes
    vk_known_lead_action_types = Column(String, nullable=True) # JSON of types already reviewed by agency
    vk_new_lead_actions_pending = Column(Boolean, nullable=False, default=False, server_default="false")

    # VK Ads personal-client OAuth link lifecycle. Existing integrations retain
    # the default active status and do not enter this flow.
    connection_status = Column(String(24), nullable=False, default="active", server_default="active", index=True)
    link_token = Column(String, nullable=True)  # encrypted opaque one-time token
    link_token_hash = Column(String(64), nullable=True, index=True)
    link_expires_at = Column(DateTime(timezone=True), nullable=True)
    link_created_at = Column(DateTime(timezone=True), nullable=True)
    link_authorized_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metrika Counters Support (for Direct integrations)
    selected_counters = Column(String, nullable=True) # JSON list of counter IDs
    utm_source = Column(String, nullable=True) # For hybrid channels like Avito Ads + Metrika leads

    # Avito Ads gets its own Yandex Metrika OAuth grant.  These credentials
    # deliberately do not reuse a Yandex Direct/Metrika integration belonging
    # to the same project: the person who connected Avito chooses the Metrika
    # account explicitly in the Avito wizard.
    metrika_access_token = Column(String, nullable=True)
    metrika_refresh_token = Column(String, nullable=True)
    metrika_account_id = Column(String, nullable=True)
    
    # Balance Support
    balance = Column(Numeric(10, 2), nullable=True) # Account balance in platform currency
    currency = Column(String(3), default="RUB") # Currency code (RUB, USD, EUR, etc.)

    client = relationship("Client", back_populates="integrations")
    campaigns = relationship("Campaign", back_populates="integration", cascade="all, delete-orphan")
    sync_jobs = relationship("SyncJob", back_populates="integration", cascade="all, delete-orphan")

    @property
    def client_name(self):
        """Property to expose client name for API responses."""
        return self.client.name if self.client else None

    @property
    def client_display_id(self):
        """Public project ID shown in the UI."""
        return self.client.display_id if self.client else None

    @property
    def metrika_connected(self) -> bool:
        """Safe boolean for the frontend; never expose the OAuth token itself."""
        return bool(self.metrika_access_token)

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    external_id = Column(String, nullable=False) # Campaign ID from the platform
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    platform_status = Column(String, nullable=True)
    platform_state = Column(String, nullable=True)
    display_status = Column(String, nullable=True)
    status_synced_at = Column(DateTime(timezone=True), nullable=True)
    vk_goal_action_id = Column(String, nullable=True)  # VK Ads goal/action identifier
    vk_goal_action_name = Column(String, nullable=True)  # VK Ads goal/action display name
    # Модель оплаты кампании (AI-комментарий, механика каналов):
    # manual_cpc | auto_cpc | pay_per_conversion
    bid_strategy = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Сопоставление кампаний по внешнему id выполняется на каждой синхронизации.
    __table_args__ = (
        Index("ix_campaigns_integration_external", "integration_id", "external_id"),
    )

    integration = relationship("Integration", back_populates="campaigns")
    yandex_stats = relationship("YandexStats", back_populates="campaign")
    yandex_groups = relationship("YandexGroups", back_populates="campaign")
    yandex_ads = relationship("YandexAds", back_populates="campaign")
    vk_stats = relationship("VKStats", back_populates="campaign")
    avito_stats = relationship("AvitoStats", back_populates="campaign")
    avito_groups = relationship("AvitoGroups", back_populates="campaign")
    avito_creatives = relationship("AvitoCreatives", back_populates="campaign")


class ProjectDirection(Base):
    __tablename__ = "project_directions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_project_directions_client_position", "client_id", "position"),
    )

    client = relationship("Client", back_populates="directions")
    masks = relationship("ProjectDirectionMask", back_populates="direction", cascade="all, delete-orphan")


class ProjectDirectionMask(Base):
    __tablename__ = "project_direction_masks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    direction_id = Column(UUID(as_uuid=True), ForeignKey("project_directions.id", ondelete="CASCADE"), nullable=False, index=True)
    mask = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    direction = relationship("ProjectDirection", back_populates="masks")


class ComparabilityEvent(Base):
    """События, ломающие сравнимость периодов (ТЗ AI-комментария, правило 7):
    смена целей/периода/атрибуции. Питает поле comparability_events контекста."""
    __tablename__ = "comparability_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(32), nullable=False)  # goals_changed | period_changed | attribution_changed
    event_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AICommentGeneration(Base):
    """Лог генераций AI-комментария и оценок (ТЗ §8) — внутренний инструмент
    качества: база для доли 👎 по версиям промпта и отбора few-shot эталонов."""
    __tablename__ = "ai_comment_generations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    period_from = Column(Date, nullable=True)
    period_to = Column(Date, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    trigger = Column(String(24), nullable=True)  # auto_sync | refresh | calculate
    text = Column(Text, nullable=True)
    fingerprint = Column(String(32), nullable=True)
    prompt_version = Column(String(16), nullable=True)
    model = Column(String(64), nullable=True)
    directions_mode = Column(String(16), nullable=True)
    vat_mode = Column(String(16), nullable=True)
    context_hash = Column(String(32), nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cache_creation_input_tokens = Column(Integer, nullable=True)
    cache_read_input_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(14, 6), nullable=True)
    cost_rub = Column(Numeric(14, 6), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    campaign_count = Column(Integer, nullable=True)
    attempt = Column(Integer, nullable=False, default=1, server_default="1")
    retry_count = Column(Integer, nullable=False, default=0, server_default="0")
    validation_failed = Column(Boolean, nullable=False, default=False, server_default="false")
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    rating = Column(Integer, nullable=True)  # 1 = 👍, -1 = 👎
    rated_by = Column(UUID(as_uuid=True), nullable=True)
    rated_at = Column(DateTime(timezone=True), nullable=True)


class TariffPlan(Base):
    __tablename__ = "tariff_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False, index=True)  # start/basic/standard
    name = Column(String, nullable=False)
    price_rub = Column(Integer, nullable=False, default=0)
    max_projects = Column(Integer, nullable=False, default=1)
    max_ai_requests_per_period = Column(Integer, nullable=False, default=30)
    period_days = Column(Integer, nullable=False, default=30)
    trial_days = Column(Integer, nullable=False, default=14)
    whitelabel_included = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("tariff_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_code = Column(String, nullable=False, default="start", index=True)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.TRIAL, index=True)
    cloudpayments_subscription_id = Column(String, nullable=True, index=True)
    cloudpayments_transaction_id = Column(String, nullable=True, index=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    # Фактический период оплаты (month/year) из платежа — без него период приходилось
    # угадывать по длине current_period (безлимитные «до 2030» выглядели годовыми).
    billing_period = Column(String, nullable=True)
    # Маска привязанной карты из вебхука CloudPayments (CardLastFour/CardType/CardExpDate).
    # Полные данные карты не покидают CloudPayments (PCI DSS) — храним только отображаемое.
    card_last4 = Column(String, nullable=True)
    card_type = Column(String, nullable=True)
    card_exp = Column(String, nullable=True)
    # Понижение тарифа применяется в конце оплаченного периода, а не сразу:
    # пользователь уже заплатил за более дорогой тариф и не должен терять его
    # досрочно. Здесь лежит код тарифа, который вступит в силу после
    # current_period_end; применяется лениво при чтении подписки.
    pending_plan_code = Column(String, nullable=True)
    pending_billing_period = Column(String, nullable=True)
    pending_purchased_project_slots = Column(Integer, nullable=True)
    # Версия прайс-бука, зафиксированная при подписке (§7.2 экономики). При выпуске
    # новой линейки аккаунт продолжает платить по своей версии, пока сам не сменит
    # тариф. Пока версия одна (см. core.pricing.PRICE_BOOK_VERSION), но поле нужно
    # завести до первых продаж, иначе потом не разобраться, кто на какой цене.
    price_book_version = Column(Integer, nullable=True)
    # Полный снимок строки прайс-бука. Одной версии недостаточно, поскольку
    # тестовые/боевые цены могут переопределяться окружением между релизами.
    price_book_snapshot = Column(JSON, nullable=True)
    pending_price_book_snapshot = Column(JSON, nullable=True)
    # Граница тарифа (§8 экономики). Докупленные слоты проектов: эффективный лимит
    # проектов = лимит тарифа + purchased_project_slots, кабинетов = лимит + слоты×3.
    purchased_project_slots = Column(Integer, nullable=False, default=0)
    # Состояние превышения. Сам факт не храним — считается как
    # active_projects > effective_projects_limit; здесь только «с какого момента»
    # и «сколько продлений подряд в превышении» (2-е продление блокирует создание).
    overflow_since = Column(DateTime(timezone=True), nullable=True)
    overflow_periods_count = Column(Integer, nullable=False, default=0)
    overflow_notice_dismissed_at = Column(DateTime(timezone=True), nullable=True)
    # Если CloudPayments временно не принял обновление суммы рекуррента, доступ
    # не отбираем, но сохраняем явный флаг для повторной синхронизации/алерта.
    recurring_sync_required = Column(Boolean, nullable=False, default=False)
    # Аналитика экономики: максимум занятых проектных слотов за текущий
    # биллинговый период и период, за который уже отправляли единственное
    # overflow-письмо за 7 дней до продления.
    peak_active_projects = Column(Integer, nullable=False, default=0)
    overflow_warning_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("TariffPlan", back_populates="subscriptions")


class BillingEvent(Base):
    """Неизменяемый журнал денежных событий.

    До него денежная история сводилась к перезаписываемым полям в subscriptions:
    нельзя было ни разобрать спор с клиентом, ни сверить обороты с CloudPayments,
    ни отличить повторную доставку вебхука от нового платежа.

    Уникальность transaction_id — механизм идемпотентности: CloudPayments
    повторяет доставку, пока не получит code 0, и без этого повтор заново
    продлевал подписку.
    """

    __tablename__ = "billing_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)

    # intent — намерение оплатить (создаётся в /billing/subscribe);
    # pay / fail / cancel / recurrent — то, что пришло вебхуком.
    event_type = Column(String(16), nullable=False, index=True)

    # Идентификатор заказа, который мы генерируем сами и передаём в виджет.
    # Позволяет связать намерение с платежом и не плодить дубли по двойному клику.
    invoice_id = Column(String(64), nullable=True, index=True)
    # TransactionId из CloudPayments — ключ идемпотентности денежных событий.
    transaction_id = Column(String(64), nullable=True)
    cp_subscription_id = Column(String(64), nullable=True, index=True)

    amount = Column(Numeric(14, 2), nullable=True)
    currency = Column(String(8), nullable=True)
    plan_code = Column(String(32), nullable=True)
    billing_period = Column(String(8), nullable=True)
    # Сырое тело уведомления — единственный способ разобрать спорный платёж.
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        # Частичный уникальный индекс: у recurrent-уведомлений TransactionId нет,
        # и NULL'ы не должны конфликтовать между собой.
        Index(
            "uq_billing_events_transaction",
            "transaction_id",
            unique=True,
            postgresql_where=text("transaction_id IS NOT NULL"),
        ),
        Index("ix_billing_events_user_created", "user_id", "created_at"),
    )

    user = relationship("User")


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), index=True, nullable=False)
    status = Column(Enum(SyncJobStatus), nullable=False, default=SyncJobStatus.QUEUED, index=True)
    stage = Column(String, nullable=True)  # queued, campaigns, stats, done
    progress = Column(Integer, nullable=False, default=0)  # 0..100
    attempt = Column(Integer, nullable=False, default=0)
    error = Column(String, nullable=True)
    params = Column(String, nullable=True)  # JSON string for lightweight compatibility
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Воркер выбирает QUEUED в порядке created_at — покрывающий индекс под это.
    __table_args__ = (
        Index("ix_sync_jobs_status_created", "status", "created_at"),
    )

    integration = relationship("Integration", back_populates="sync_jobs")

class YandexStats(Base):
    __tablename__ = "yandex_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)
    ctr = Column(Numeric(10, 4))
    cpc = Column(Numeric(20, 2))

    # Индексы обязаны быть и здесь, и в миграции: объявленные только в alembic
    # пропадают при пересоздании базы через create_all().
    __table_args__ = (
        Index("ix_yandex_stats_client_date_campaign", "client_id", "date", "campaign_id"),
        Index("ix_yandex_stats_campaign_id", "campaign_id"),
    )

    client = relationship("Client", back_populates="yandex_stats")
    campaign = relationship("Campaign", back_populates="yandex_stats")

class YandexKeywords(Base):
    __tablename__ = "yandex_keywords"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    keyword = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)

    # Ключ поиска при апсерте: без него каждый SELECT существующей строки шёл
    # через BitmapAnd по двум одиночным индексам.
    __table_args__ = (
        Index("ix_yandex_keywords_lookup", "client_id", "date", "campaign_name", "keyword"),
    )

    client = relationship("Client", back_populates="yandex_keywords")

class YandexGroups(Base):
    __tablename__ = "yandex_groups"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_id = Column(String, nullable=True, index=True)
    group_name = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)

    __table_args__ = (
        Index("ix_yandex_groups_lookup", "client_id", "campaign_id", "date", "group_id"),
    )

    client = relationship("Client", back_populates="yandex_groups")
    campaign = relationship("Campaign", back_populates="yandex_groups")


class YandexAds(Base):
    __tablename__ = "yandex_ads"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_id = Column(String, nullable=True, index=True)
    group_name = Column(String, nullable=True)
    ad_id = Column(String, nullable=True, index=True)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)

    client = relationship("Client", back_populates="yandex_ads")
    campaign = relationship("Campaign", back_populates="yandex_ads")

class AvitoStats(Base):
    __tablename__ = "avito_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)
    cpc = Column(Numeric(20, 2), nullable=True)
    cpa = Column(Numeric(20, 2), nullable=True)

    __table_args__ = (
        Index("ix_avito_stats_client_date_campaign", "client_id", "date", "campaign_id"),
    )

    client = relationship("Client", back_populates="avito_stats")
    campaign = relationship("Campaign", back_populates="avito_stats")


class VKGroups(Base):
    """Дневная статистика групп объявлений VK Ads (уровень ad_groups) — для
    drill-down иерархии кампаний, по образцу yandex_groups. Заполняется лениво
    при первом раскрытии кампании. Конверсии — родные vk.goals уровня группы."""
    __tablename__ = "vk_groups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_id = Column(String, nullable=True, index=True)
    group_name = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)

    client = relationship("Client", backref="vk_groups")
    campaign = relationship("Campaign", backref="vk_groups")


class VKBanners(Base):
    """Дневная статистика объявлений VK Ads (уровень banners) — третий уровень
    drill-down, по образцу yandex_ads."""
    __tablename__ = "vk_banners"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_id = Column(String, nullable=True, index=True)
    group_name = Column(String, nullable=True)
    banner_id = Column(String, nullable=True, index=True)
    banner_name = Column(String, nullable=True)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)

    client = relationship("Client", backref="vk_banners")
    campaign = relationship("Campaign", backref="vk_banners")


class AvitoGroups(Base):
    __tablename__ = "avito_groups"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_id = Column(String, nullable=True, index=True)
    group_name = Column(String, nullable=True)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)
    cpc = Column(Numeric(20, 2), nullable=True)
    cpa = Column(Numeric(20, 2), nullable=True)

    client = relationship("Client", back_populates="avito_groups")
    campaign = relationship("Campaign", back_populates="avito_groups")


class AvitoCreatives(Base):
    __tablename__ = "avito_creatives"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_id = Column(String, nullable=True, index=True)
    creative_id = Column(String, nullable=True, index=True)
    creative_name = Column(String, nullable=True)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)
    cpc = Column(Numeric(20, 2), nullable=True)
    cpa = Column(Numeric(20, 2), nullable=True)

    client = relationship("Client", back_populates="avito_creatives")
    campaign = relationship("Campaign", back_populates="avito_creatives")


class VKStats(Base):
    __tablename__ = "vk_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)  # vk.goals - Результат (лиды)
    cpc = Column(Numeric(20, 2), nullable=True)  # Средняя цена клика из VK API
    cpa = Column(Numeric(20, 2), nullable=True)  # vk.cpa - Средняя цена цели из VK API

    __table_args__ = (
        Index("ix_vk_stats_client_date_campaign", "client_id", "date", "campaign_id"),
        Index("ix_vk_stats_campaign_id", "campaign_id"),
    )

    client = relationship("Client", back_populates="vk_stats")
    campaign = relationship("Campaign", back_populates="vk_stats")

class MetrikaGoals(Base):
    __tablename__ = "metrika_goals"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=True, index=True)
    date = Column(Date, index=True, nullable=False)
    goal_id = Column(String, nullable=False)
    goal_name = Column(String)
    conversion_count = Column(Integer, default=0)

    # client_id раньше не был проиндексирован вовсе, хотя это одна из самых
    # читаемых таблиц: без индекса выборка по проекту шла по всем арендаторам.
    __table_args__ = (
        Index("ix_metrika_goals_client_date_goal", "client_id", "date", "goal_id"),
        Index("ix_metrika_goals_integration_date", "integration_id", "date"),
    )

    # Relationships
    integration = relationship("Integration", foreign_keys=[integration_id])

class ProjectBudget(Base):
    __tablename__ = "project_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    # NULL is a project-wide plan.  Per-channel budgets take precedence over it.
    channel = Column(Enum(IntegrationPlatform), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    # A manually agreed lead count.  NULL means "derive it from budget / summary CPL".
    manual_leads = Column(Integer, nullable=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="budgets")


class ProjectTargetCPA(Base):
    __tablename__ = "project_target_cpa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(Enum(IntegrationPlatform), nullable=True)
    goal_id = Column(String, nullable=True)
    goal_name = Column(String, nullable=True)
    is_summary = Column(Boolean, default=False, nullable=False)
    target_cpa = Column(Numeric(14, 2), nullable=True)
    control_enabled = Column(Boolean, default=False, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="target_cpas")


class DetectorAlert(Base):
    __tablename__ = "detector_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric = Column(String(32), nullable=False)
    detection_level = Column(String(32), nullable=False, default="project")
    entity_id = Column(String(128), nullable=True)
    channel = Column(Enum(IntegrationPlatform), nullable=True)
    # Detector v3 has explicit critical modes such as ``critical_tracking``
    # (17 chars).  Keep headroom for future named checks instead of coupling
    # alert persistence to the shortest historical values.
    mode = Column(String(32), nullable=False, default="baseline")
    severity = Column(String(16), nullable=False, default="warning")
    deviation_pct = Column(Numeric(8, 2), nullable=True)
    baseline_value = Column(Numeric(20, 2), nullable=True)
    actual_value = Column(Numeric(20, 2), nullable=True)
    consecutive_days = Column(Integer, nullable=False, default=1)
    pattern_key = Column(String(64), nullable=True)
    # Composite plan/fact diagnoses contain the primary problem, related plan
    # checks and contributing campaigns; 500 chars truncates valid context.
    hypothesis_text = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, default="open", index=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    snoozed_until = Column(DateTime(timezone=True), nullable=True, index=True)
    snooze_source = Column(JSON, nullable=True)
    not_problem_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)

    client = relationship("Client")
    owner = relationship("User", foreign_keys=[owner_id])

    __table_args__ = (
        UniqueConstraint(
            "client_id", "metric", "detection_level", "entity_id", "channel", "mode",
            name="uq_detector_alert_open",
        ),
        Index("ix_detector_alerts_client_status", "client_id", "status"),
        Index("ix_detector_alerts_owner_status", "owner_id", "status"),
    )


class DetectorAlertView(Base):
    """Персональное состояние «увидел» (детектор ит.4, §9.1).

    Пара алерт × пользователь: у каждого сотрудника своя новизна. Снимок
    severity/deviation/actual/baseline фиксирует «было» на момент просмотра —
    отсюда фраза «было в 1,3 раза, стало в 2,1» (§9.4). ``acknowledged`` —
    явное «Понятно»: жёлтый гасит любой просмотр, красный — только явное
    подтверждение (§8).
    """

    __tablename__ = "detector_alert_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("detector_alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    seen_severity = Column(String(16), nullable=True)
    seen_deviation_pct = Column(Numeric(8, 2), nullable=True)
    seen_actual_value = Column(Numeric(20, 2), nullable=True)
    seen_baseline_value = Column(Numeric(20, 2), nullable=True)
    acknowledged = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("alert_id", "user_id", name="uq_detector_alert_view"),
    )


class DetectorProjectVisit(Base):
    """Дата последнего захода пользователя в проект (детектор ит.4, §9.3).

    Заголовок «Новое с 24 июля» считается от предыдущего захода, а не от
    календарных суток: ``previous_viewed_at`` — заход перед текущим, к нему и
    относится «новое».
    """

    __tablename__ = "detector_project_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    last_viewed_at = Column(DateTime(timezone=True), nullable=True)
    previous_viewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_detector_project_visit"),
    )


class AIAssistantDialog(Base):
    __tablename__ = "ai_assistant_dialogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False, default="Новый диалог")
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
    client = relationship("Client")
    messages = relationship(
        "AIAssistantMessage",
        back_populates="dialog",
        cascade="all, delete-orphan",
        order_by="AIAssistantMessage.created_at",
    )


class AIAssistantMessage(Base):
    __tablename__ = "ai_assistant_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dialog_id = Column(UUID(as_uuid=True), ForeignKey("ai_assistant_dialogs.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(String, nullable=False)
    cost_requests = Column(Integer, nullable=False, default=0)
    redirect_target = Column(String(32), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dialog = relationship("AIAssistantDialog", back_populates="messages")


class AIAssistantPrompt(Base):
    __tablename__ = "ai_assistant_prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    total_cost = Column(Numeric(20, 2), default=0)
    total_clicks = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    avg_cpc = Column(Numeric(20, 2), default=0)
    avg_cpa = Column(Numeric(20, 2), default=0)

    client = relationship("Client", back_populates="weekly_reports")

class MonthlyReport(Base):
    __tablename__ = "monthly_reports"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    month = Column(Integer, nullable=False) # 1-12
    year = Column(Integer, nullable=False)
    total_cost = Column(Numeric(20, 2), default=0)
    total_clicks = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    avg_cpc = Column(Numeric(20, 2), default=0)
    avg_cpa = Column(Numeric(20, 2), default=0)

    client = relationship("Client", back_populates="monthly_reports")

# ============================================================================
# Phone Validation Models
# ============================================================================

class PhoneProject(Base):
    """
    Проект для валидации телефонов.
    Аналогично Client для интеграций, но для телефонии.
    Проекты независимы - разные node.
    """
    __tablename__ = "phone_projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)  # Связь с клиентом (опционально)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # Настройки проекта
    webhook_url = Column(String, nullable=True)  # Уникальный URL для webhook этого проекта
    webhook_secret = Column(String, nullable=True)  # Секрет для подписи webhook запросов
    
    # Настройки выгрузки
    crm_webhook_url = Column(String, nullable=True)  # URL для отправки в CRM
    email_recipients = Column(String, nullable=True)  # JSON массив email адресов
    telegram_chat_id = Column(String, nullable=True)  # Telegram chat ID для уведомлений
    
    # Настройки валидации
    enable_social_check = Column(Boolean, default=False)  # Проверка соцсетей
    enable_lead_scoring = Column(Boolean, default=False)  # Скоринг lead_score / qualification_tier
    enable_gosuslugi_check = Column(Boolean, default=False)  # Проверка Госуслуг
    enable_spam_check = Column(Boolean, default=True)  # Проверка спам-баз (по умолчанию вкл)
    enable_bitrix_check = Column(Boolean, default=False)  # Проверка дубликатов в Bitrix24
    enable_metrica_export = Column(Boolean, default=True)  # Отправка в Яндекс.Метрику
    
    # Настройки CAPTCHA (клиент использует свои ключи)
    captcha_provider = Column(String, nullable=True, default='none')  # turnstile, recaptcha, smartcaptcha, none
    captcha_site_key = Column(String, nullable=True)  # Публичный ключ (показывается в коде клиента)
    captcha_secret_key = Column(String, nullable=True)  # Секретный ключ (только для backend валидации)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    client = relationship("Client", foreign_keys=[client_id])
    leads = relationship("Lead", back_populates="project", cascade="all, delete-orphan")


class Notification(Base):
    """In-app уведомления пользователя."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(64), nullable=False)   # sync_failed | payment_ok | payment_failed | limit_warn | system
    title = Column(String(255), nullable=False)
    body = Column(String(1000), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    meta = Column(JSON, nullable=True)          # доп. данные: integration_id, plan_code и т.д.

    user = relationship("User", backref="notifications")


class HistoryEvent(Base):
    """Аудит действий внутри рабочего пространства команды."""
    __tablename__ = "history_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_name = Column(String(255), nullable=True)
    actor_role = Column(String(32), nullable=True)
    event_type = Column(String(64), nullable=False, index=True)  # team | project | integration | ai | billing
    action = Column(String(128), nullable=False)
    description = Column(String(1000), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type = Column(String(64), nullable=True)
    target_id = Column(String(128), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class LeadStatus(enum.Enum):
    """Статус заявки"""
    PENDING = "PENDING"  # В обработке
    VALID = "VALID"  # Валидная заявка
    SPAM = "SPAM"  # Помечена как спам
    INVALID = "INVALID"  # Не прошла валидацию


class Lead(Base):
    """
    Заявка (лид) с полными данными для валидации.
    Сохраняется в базу со всеми параметрами из скриншота.
    """
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("phone_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Основные данные
    phone = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    surname = Column(String, nullable=True)  # Фамилия (заполняется из соцсетей/Госуслуг)
    
    # Данные из заявки (ответы на вопросы, дополнительные поля)
    form_data = Column(String, nullable=True)  # JSON с дополнительными данными формы
    
    # UTM метки
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    utm_content = Column(String, nullable=True)
    utm_term = Column(String, nullable=True)
    
    # Технические данные
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    referer = Column(String, nullable=True)
    geo_country = Column(String, nullable=True)
    browser_timezone = Column(String, nullable=True)
    ym_uid = Column(String, nullable=True)  # Яндекс.Метрика client ID
    fingerprint = Column(String, nullable=True)  # Browser fingerprint
    
    # Данные валидации (стадия 1)
    is_valid = Column(Boolean, default=False)  # Прошла ли валидацию
    validation_reason = Column(String, nullable=True)  # Причина отклонения или подтверждения
    phone_type = Column(String, nullable=True)  # Мобильный/Стационарный
    phone_provider = Column(String, nullable=True)  # Оператор связи
    phone_region = Column(String, nullable=True)  # Регион
    phone_city = Column(String, nullable=True)  # Город
    dadata_qc = Column(Integer, nullable=True)  # Код качества DaData
    
    # Данные обогащения (стадия 2)
    main_operator = Column(String, nullable=True)  # Основной оператор
    registrant_info = Column(String, nullable=True)  # На кого зарегистрирован
    
    # Проверка соцсетей
    has_telegram = Column(Boolean, nullable=True)
    has_whatsapp = Column(Boolean, nullable=True)
    has_viber = Column(Boolean, nullable=True)
    has_tiktok = Column(Boolean, nullable=True)  # TT
    has_vk = Column(Boolean, nullable=True)  # BK
    social_accounts_data = Column(String, nullable=True)  # JSON с данными аккаунтов

    lead_score = Column(Integer, nullable=True)  # 0–100
    qualification_tier = Column(String, nullable=True)  # low | medium | high
    
    # Проверка Госуслуг
    has_gosuslugi = Column(Boolean, nullable=True)
    gosuslugi_name = Column(String, nullable=True)  # Имя из Госуслуг
    gosuslugi_surname = Column(String, nullable=True)  # Фамилия из Госуслуг
    
    # Статус и пометки
    status = Column(Enum(LeadStatus), default=LeadStatus.PENDING, index=True)
    is_spam = Column(Boolean, default=False, index=True)
    is_verified = Column(Boolean, default=False)  # Пометка "проверено"
    
    # Выгрузка
    exported_to_crm = Column(Boolean, default=False)
    exported_to_email = Column(Boolean, default=False)
    exported_to_telegram = Column(Boolean, default=False)
    exported_to_metrica = Column(Boolean, default=False)
    export_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("PhoneProject", back_populates="leads")
