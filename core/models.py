import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer, Numeric, Date, Enum, BigInteger, Boolean, UniqueConstraint, JSON, Sequence
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"

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


class TelegramLinkToken(Base):
    """
    Одноразовый токен для deep link t.me/<bot>?start=<token>.
    После /start в Telegram webhook привязывает chat_id к пользователю.
    """

    __tablename__ = "telegram_link_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
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
    status = Column(Enum(ClientStatus), default=ClientStatus.ACTIVE, nullable=False, server_default="ACTIVE")
    detector_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    actual_start_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_ai_comment = Column(Text, nullable=True)
    last_ai_comment_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="clients")
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
    access_token = Column(String, nullable=False) # Should be encrypted in production
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

    # Goals Support
    selected_goals = Column(String, nullable=True) # JSON list of goal IDs
    primary_goal_id = Column(String, nullable=True)
    
    # Metrika Counters Support (for Direct integrations)
    selected_counters = Column(String, nullable=True) # JSON list of counter IDs
    utm_source = Column(String, nullable=True) # For hybrid channels like Avito Ads + Metrika leads
    
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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

    client = relationship("Client", back_populates="directions")
    masks = relationship("ProjectDirectionMask", back_populates="direction", cascade="all, delete-orphan")


class ProjectDirectionMask(Base):
    __tablename__ = "project_direction_masks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    direction_id = Column(UUID(as_uuid=True), ForeignKey("project_directions.id", ondelete="CASCADE"), nullable=False, index=True)
    mask = Column(String, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    direction = relationship("ProjectDirection", back_populates="masks")


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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("TariffPlan", back_populates="subscriptions")


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

    client = relationship("Client", back_populates="avito_stats")
    campaign = relationship("Campaign", back_populates="avito_stats")


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
    
    # Relationships
    integration = relationship("Integration", foreign_keys=[integration_id])

class ProjectBudget(Base):
    __tablename__ = "project_budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(Enum(IntegrationPlatform), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
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
    mode = Column(String(16), nullable=False, default="baseline")
    severity = Column(String(16), nullable=False, default="warning")
    deviation_pct = Column(Numeric(8, 2), nullable=True)
    baseline_value = Column(Numeric(20, 2), nullable=True)
    actual_value = Column(Numeric(20, 2), nullable=True)
    consecutive_days = Column(Integer, nullable=False, default=1)
    pattern_key = Column(String(64), nullable=True)
    hypothesis_text = Column(String(500), nullable=True)
    status = Column(String(16), nullable=False, default="open", index=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
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
