from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
import json

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    two_factor_enabled: bool = False
    interface_language: str = "ru"
    notification_email: Optional[EmailStr] = None
    yandex_finance_token: Optional[str] = None
    report_telegram_chat_id: Optional[str] = None
    report_max_chat_id: Optional[str] = None
    report_max_user_id: Optional[str] = None
    report_max_username: Optional[str] = None
    report_delivery_channels: Optional[List[str]] = None  # telegram, max
    report_email_recipients: Optional[List[str]] = None  # Массив email для отчётов
    report_schedule: Optional[str] = None  # JSON {"day":"daily","time":"10:00"}

    @field_validator("report_email_recipients", mode="before")
    @classmethod
    def parse_email_recipients(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return v
        try:
            return json.loads(v) if v else []
        except Exception:
            return []

    @field_validator("report_delivery_channels", mode="before")
    @classmethod
    def parse_report_delivery_channels(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return v
        try:
            return json.loads(v) if v else []
        except Exception:
            return []

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime
    email_verified: bool = False
    is_subscribed: bool = False
    subscription_expires_at: Optional[datetime] = None
    brand_logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    brand_pdf_header: Optional[str] = None
    brand_pdf_signature: Optional[str] = None
    brand_custom_domain: Optional[str] = None
    brand_domain_status: Optional[str] = None
    whitelabel_available: bool = False
    has_password: bool = True
    password_updated_at: Optional[datetime] = None
    global_detector_enabled: bool = True

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


class OAuthAuthorizeUrlResponse(BaseModel):
    """URL для редиректа браузера на страницу авторизации провайдера (Яндекс / VK / MAX)."""

    url: str
    state: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    poll_interval_ms: Optional[int] = None


class OAuthLoginCallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str
    # VK ID OAuth 2.1 callback параметры (PKCE).
    device_id: Optional[str] = None
    code_verifier: Optional[str] = None
    # Legacy поле для старого VK Ads login flow. Оставлено для обратной совместимости.
    vk_redirect_user_id: Optional[str] = None
    remember_me: bool = True


class MaxOAuthStatusResponse(BaseModel):
    status: str  # pending | completed | expired | used
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in_seconds: Optional[int] = None


class TelegramDeepLinkResponse(BaseModel):
    """Ссылка для открытия Telegram в чате с ботом (кнопка Start)."""

    deep_link: str
    expires_in_seconds: int = 900


class RegisterPendingResponse(BaseModel):
    """Регистрация без JWT — нужно подтвердить почту."""
    email: EmailStr
    message: str = "Проверьте почту и перейдите по ссылке для подтверждения."

class LoginPasswordStepResponse(BaseModel):
    """Ответ POST /auth/login (пароль), без JWT."""
    step: str  # otp_required | email_not_verified
    challenge_id: Optional[UUID] = None
    email_masked: Optional[str] = None
    email: Optional[EmailStr] = None

class LoginResponse(BaseModel):
    """
    Универсальный ответ POST /auth/login:
    - при включенном OTP: step/challenge_id
    - при отключенном OTP: access_token/token_type
    """
    step: Optional[str] = None  # otp_required | email_not_verified
    challenge_id: Optional[UUID] = None
    email_masked: Optional[str] = None
    email: Optional[EmailStr] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetConfirmBody(BaseModel):
    token: str
    new_password: str

class LoginVerifyRequest(BaseModel):
    challenge_id: UUID
    code: str
    remember_me: bool = False


class TwoFactorSetupVerifyRequest(BaseModel):
    challenge_id: UUID
    code: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class TokenData(BaseModel):
    email: Optional[str] = None


class UserUpdateSettings(BaseModel):
    """
    Обновление настроек текущего пользователя.
    Пока даём редактировать только безопасные поля (имя, фамилия, FinanceToken, отчёты).
    """
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    notification_email: Optional[EmailStr] = None
    interface_language: Optional[str] = None
    two_factor_enabled: Optional[bool] = None
    global_detector_enabled: Optional[bool] = None
    yandex_finance_token: Optional[str] = None
    report_telegram_chat_id: Optional[str] = None
    report_max_chat_id: Optional[str] = None
    report_max_user_id: Optional[str] = None
    report_max_username: Optional[str] = None
    report_delivery_channels: Optional[List[str]] = None
    report_email_recipients: Optional[List[str]] = None
    report_schedule: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str


class OAuthIdentityStatus(BaseModel):
    provider: str
    label: str
    short: Optional[str] = None
    icon_url: Optional[str] = None
    connected: bool
    can_unlink: bool = False
    hint: Optional[str] = None


class TeamProjectRef(BaseModel):
    id: UUID
    name: str


class TeamMemberResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    email: EmailStr
    role: str
    status: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    full_name: Optional[str] = None
    projects: List[TeamProjectRef] = []


class TeamInviteRequest(BaseModel):
    email: EmailStr
    role: Optional[str] = None


class TeamGrantProjectRequest(BaseModel):
    project_id: UUID


class TeamMemberUpdateRequest(BaseModel):
    role: str


class TeamContextResponse(BaseModel):
    is_owner: bool
    team_role: Optional[str] = None
    account_id: Optional[UUID] = None


class HistoryEventResponse(BaseModel):
    id: UUID
    account_id: UUID
    actor_user_id: Optional[UUID] = None
    actor_email: Optional[str] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    event_type: str
    action: str
    description: Optional[str] = None
    client_id: Optional[UUID] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    meta: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

from core import models

# Integration Schemas
class IntegrationBase(BaseModel):
    platform: models.IntegrationPlatform
    account_id: Optional[str] = None
    account_name: Optional[str] = None  # Human-readable cabinet name (Yandex ClientInfo, etc.)
    auto_sync: Optional[bool] = True
    sync_interval: Optional[int] = 1440
    selected_goals: Optional[List[str]] = None # List of goal IDs
    primary_goal_id: Optional[str] = None

    @field_validator('selected_goals', mode='before')
    @classmethod
    def parse_selected_goals(cls, v: Any) -> Any:
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except:
                return []
        return v

    @field_validator('platform', mode='before')
    @classmethod
    def normalize_platform(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

class IntegrationCreate(IntegrationBase):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    client_name: Optional[str] = None # Make optional to avoid 422 if not provided

class IntegrationResponse(IntegrationBase):
    id: UUID
    client_id: UUID
    client_name: Optional[str] = None  # Project name for frontend display
    client_display_id: Optional[int] = None
    access_token: str
    expires_at: Optional[datetime] = None
    agency_client_login: Optional[str] = None
    is_agency: Optional[bool] = None
    selected_goals: Optional[List[str]] = None
    primary_goal_id: Optional[str] = None
    selected_counters: Optional[List[str]] = None
    balance: Optional[float] = None
    currency: Optional[str] = None
    campaigns: List["CampaignResponse"] = []
    sync_status: Optional[str] = None  # SUCCESS | FAILED | PENDING | NEVER
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None

    @field_validator('selected_counters', mode='before')
    @classmethod
    def parse_selected_counters(cls, v: Any) -> Any:
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except:
                return []
        return v

    class Config:
        from_attributes = True

# Campaign Schemas
class CampaignBase(BaseModel):
    external_id: str
    name: str
    is_active: bool = True
    platform_status: Optional[str] = None
    platform_state: Optional[str] = None
    display_status: Optional[str] = None
    status_synced_at: Optional[datetime] = None

class CampaignCreate(CampaignBase):
    integration_id: UUID

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    client_id: Optional[UUID] = None # For moving campaign between projects (effectively changing integration/client)

class CampaignResponse(CampaignBase):
    id: UUID
    integration_id: UUID
    vk_goal_action_id: Optional[str] = None
    vk_goal_action_name: Optional[str] = None
    
    class Config:
        from_attributes = True

IntegrationResponse.model_rebuild()

# Stats Schemas
class StatsTrend(BaseModel):
    expenses: float = 0
    impressions: float = 0
    clicks: float = 0
    leads: float = 0
    cpc: float = 0
    cpa: float = 0
    ctr: float = 0
    cr: float = 0

class StatsSummary(BaseModel):
    expenses: float
    impressions: int
    clicks: int
    leads: int
    cpc: float
    cpa: float
    ctr: float = 0
    cr: float = 0
    # NEW: dashboard expects balance & currency for proper display
    # CRITICAL: balance can be None if not available for the selected profile
    balance: Optional[float] = None
    currency: Optional[str] = None
    leads_available: bool = True
    cpa_available: bool = True
    goals_syncing: bool = False
    goals_sync_message: Optional[str] = None
    trends: Optional[StatsTrend] = None

# Client Schemas
class ClientBase(BaseModel):
    name: str
    description: Optional[str] = None
    spreadsheet_id: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    site_url: Optional[str] = None
    direction_label: Optional[str] = None
    detector_enabled: Optional[bool] = None
    status: Optional[str] = None

class ClientResponse(ClientBase):
    id: UUID
    display_id: Optional[int] = None
    owner_id: UUID
    avatar_url: Optional[str] = None
    site_url: Optional[str] = None
    direction_label: str = "directions"
    status: Optional[str] = "active"
    detector_enabled: Optional[bool] = False
    actual_start_date: Optional[str] = None
    created_at: datetime
    integrations: List[IntegrationResponse] = []
    summary: Optional[StatsSummary] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        if hasattr(v, "value"):
            return v.value.lower()
        return str(v).lower() if v else "active"

    @field_validator("actual_start_date", mode="before")
    @classmethod
    def normalize_date(cls, v):
        if v is None:
            return None
        return str(v)

    class Config:
        from_attributes = True


class DirectionMaskResponse(BaseModel):
    id: UUID
    mask: str
    position: int = 0

    class Config:
        from_attributes = True


class ProjectDirectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    masks: List[str] = Field(default_factory=list)


class ProjectDirectionCreate(ProjectDirectionBase):
    position: Optional[int] = None


class ProjectDirectionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    masks: Optional[List[str]] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


class ProjectDirectionResponse(BaseModel):
    id: UUID
    client_id: UUID
    name: str
    position: int = 0
    is_active: bool = True
    masks: List[DirectionMaskResponse] = []
    campaign_ids: List[str] = []
    campaign_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DirectionLabelUpdate(BaseModel):
    label: str = Field(default="directions", max_length=32)


class DirectionPreviewRequest(BaseModel):
    name: Optional[str] = None
    masks: List[str] = Field(default_factory=list)
    exclude_direction_id: Optional[UUID] = None
    platform: Optional[str] = "all"


class DirectionPreviewCampaign(BaseModel):
    id: str
    name: str
    platform: str
    status: str = "active"
    status_label: str = "Активна"
    selected: bool = False
    is_active: bool = True
    matched_mask: Optional[str] = None
    conflict_direction_id: Optional[str] = None
    conflict_direction_name: Optional[str] = None


class DirectionPreviewResponse(BaseModel):
    total_campaigns: int = 0
    matched_count: int = 0
    conflict_count: int = 0
    campaigns: List[DirectionPreviewCampaign] = []


class DirectionReorderRequest(BaseModel):
    direction_ids: List[UUID]


class DirectionSuggestion(BaseModel):
    name: str
    masks: List[str]
    matched_count: int
    campaign_ids: List[str] = []


class DirectionStatsItem(BaseModel):
    id: str
    name: str
    is_unassigned: bool = False
    campaign_ids: List[str] = []
    campaign_count: int = 0
    impressions: int = 0
    expenses: float = 0
    budget_share: float = 0
    leads: int = 0
    cpl: float = 0
    trend: float = 0


class DirectionStatsResponse(BaseModel):
    label: str = "Направления"
    label_key: str = "directions"
    mode: str = "cards"
    total_expenses: float = 0
    items: List[DirectionStatsItem] = []


class ProjectBudgetItem(BaseModel):
    integration_id: Optional[str] = None
    channel: Optional[str] = None
    amount: float = Field(ge=0)
    period_start: Optional[str] = None
    period_end: Optional[str] = None

class ProjectBudgetResponse(BaseModel):
    id: UUID
    channel: str
    amount: float
    period_start: str
    period_end: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("channel", mode="before")
    @classmethod
    def normalize_channel(cls, v):
        if hasattr(v, "value"):
            return v.value
        return v

    @field_validator("period_start", "period_end", mode="before")
    @classmethod
    def normalize_date(cls, v):
        if v is None:
            return None
        return str(v)

class ProjectTargetCPAItem(BaseModel):
    integration_id: Optional[str] = None
    channel: Optional[str] = None
    goal_id: Optional[str] = None
    goal_name: Optional[str] = None
    is_summary: bool = False
    target_cpa: Optional[float] = Field(default=None, ge=0)
    control_enabled: bool = False
    period_start: Optional[str] = None
    period_end: Optional[str] = None

class ProjectTargetCPAResponse(BaseModel):
    id: UUID
    channel: Optional[str] = None
    goal_id: Optional[str] = None
    goal_name: Optional[str] = None
    is_summary: bool = False
    target_cpa: Optional[float] = None
    control_enabled: bool = False
    period_start: str
    period_end: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("channel", mode="before")
    @classmethod
    def normalize_channel(cls, v):
        if v is None:
            return None
        if hasattr(v, "value"):
            return v.value
        return v

    @field_validator("period_start", "period_end", mode="before")
    @classmethod
    def normalize_date(cls, v):
        if v is None:
            return None
        return str(v)


class ProjectDetectorState(BaseModel):
    status: str
    actual_start_date: Optional[str] = None
    days_since_start: Optional[int] = None
    warmup_days: int = 21
    message: str


class ProjectSettingsResponse(BaseModel):
    project: ClientResponse
    integration_state: str
    detector_state: ProjectDetectorState
    budgets: List[ProjectBudgetResponse] = []
    target_cpa: List[ProjectTargetCPAResponse] = []


class GoogleSheetsConnectRequest(BaseModel):
    spreadsheet_id: str


class GoogleSheetsStatusResponse(BaseModel):
    spreadsheet_id: Optional[str] = None
    connected: bool = False
    configured: bool = False
    service_account_email: Optional[str] = None
    spreadsheet_title: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    last_export: Optional[Any] = None
    message: Optional[str] = None


class DetectorAlertResponse(BaseModel):
    id: UUID
    metric: str
    detection_level: str
    entity_id: Optional[str] = None
    channel: Optional[str] = None
    mode: str
    severity: str
    deviation_pct: Optional[float] = None
    baseline_value: Optional[float] = None
    actual_value: Optional[float] = None
    consecutive_days: int = 1
    pattern_key: Optional[str] = None
    hypothesis_text: Optional[str] = None
    status: str
    opened_at: datetime

    class Config:
        from_attributes = True

    @field_validator("channel", mode="before")
    @classmethod
    def normalize_channel(cls, v):
        if v is None:
            return None
        if hasattr(v, "value"):
            return v.value
        return v


class DetectorSummaryResponse(BaseModel):
    warning_count: int = 0
    problem_count: int = 0
    max_severity: Optional[str] = None
    warmup_status: Optional[str] = None
    warmup_days_left: Optional[int] = None
    alerts: List[DetectorAlertResponse] = []


class DetectorCrossProjectItem(BaseModel):
    project_id: UUID
    warning_count: int = 0
    problem_count: int = 0
    max_severity: Optional[str] = None
    warmup_status: Optional[str] = None


class DynamicsStat(BaseModel):
    labels: List[str]
    costs: List[float]
    clicks: List[int]
    impressions: List[int]
    leads: List[int]
    cpc: List[float]
    cpa: List[float]

class CampaignStat(BaseModel):
    id: Optional[str] = None
    name: str
    impressions: int
    clicks: int
    cost: float
    conversions: int
    cpc: float
    cpa: float
    trend_cost: Optional[float] = None
    trend_impressions: Optional[float] = None
    trend_clicks: Optional[float] = None
    trend_conversions: Optional[float] = None
    trend_cpc: Optional[float] = None
    trend_cpa: Optional[float] = None

class VkGoalAction(BaseModel):
    id: str
    name: str

class KeywordStat(BaseModel):
    keyword: str
    campaign_name: str
    impressions: int
    clicks: int
    cost: float
    conversions: int
    cpc: float
    cpa: float

class GroupStat(BaseModel):
    name: str
    campaign_name: str
    impressions: int
    clicks: int
    cost: float
    conversions: int
    cpc: float
    cpa: float
    
class TopClient(BaseModel):
    name: str
    expenses: float
    percentage: float

class GoalStat(BaseModel):
    id: Optional[str] = None  # Goal ID from Metrika
    name: str
    count: int
    trend: float
    cost: Optional[float] = 0.0  # Cost for this goal (proportional to conversions)
    syncing: bool = False
    missing_in_metrika: bool = False

class IntegrationStatus(BaseModel):
    platform: str
    is_connected: bool


class DashboardIntegrationStatus(BaseModel):
    """Integration status with balance for dashboard display."""
    platform: str
    is_connected: bool
    balance: Optional[float] = None
    currency: Optional[str] = None
    last_sync_at: Optional[datetime] = None

class SyncRequest(BaseModel):
    days: int = 7
    force_full: bool = False


class SyncJobResponse(BaseModel):
    id: UUID
    integration_id: UUID
    status: str
    stage: Optional[str] = None
    progress: int = 0
    attempt: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# Error Schema
class ErrorResponse(BaseModel):
    detail: str


class BillingPlanResponse(BaseModel):
    code: str
    name: str
    price_rub: int
    max_projects: int
    max_cabinets: int = 0
    max_users: int = 1
    max_staff: int = 1
    max_clients: int = 0
    max_ai_requests_per_period: int
    period_days: int
    trial_days: int
    whitelabel_included: bool = False
    is_default: bool
    is_active: bool


class BillingSubscriptionResponse(BaseModel):
    plan_code: str
    plan_name: str
    status: str
    is_subscribed: bool
    billing_period: str = "month"
    subscription_expires_at: Optional[datetime] = None
    max_projects: int
    projects_used: int = 0
    paused_projects: int = 0
    max_cabinets: int = 0
    cabinets_used: int = 0
    max_users: int = 1
    users_used: int = 1
    max_staff: int = 1
    max_clients: int = 0
    max_ai_requests_per_period: int
    ai_requests_used: int
    ai_requests_remaining: int
    ai_reset_date: Optional[str] = None
    period_days: int
    autorenew: bool = True
    payment_method: Optional[Any] = None
    whitelabel_available: bool = False


class BillingSubscribeRequest(BaseModel):
    plan_code: str
    billing_period: str = "month"
    success_url: Optional[str] = None
    fail_url: Optional[str] = None


class BillingRecurrentParams(BaseModel):
    """Параметры рекуррентного списания для виджета CloudPayments (data.cloudPayments.recurrent)."""

    interval: str
    period: int = 1


class BillingSubscribeResponse(BaseModel):
    public_id: str
    amount: int
    currency: str
    description: str
    account_id: str
    email: str
    plan_code: str
    billing_period: str = "month"
    trial_days: int
    recurrent: Optional[BillingRecurrentParams] = None
    # Объект чека для CloudPayments/CloudKassir (options.receipt в виджете).
    receipt: Optional[dict] = None


class CloudPaymentsWebhookResponse(BaseModel):
    code: int = 0
