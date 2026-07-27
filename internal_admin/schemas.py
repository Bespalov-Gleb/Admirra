"""Pydantic-схемы internal_admin."""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None
    recovery_code: Optional[str] = None
    mfa_token: Optional[str] = None


class AdminTokenResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    role: str | None = None
    full_name: Optional[str] = None
    requires_2fa: bool = False
    mfa_token: Optional[str] = None


class AdminMeResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    role_label: str
    full_name: Optional[str] = None
    permissions: dict[str, bool]


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    target_user_id: UUID
    expires_in_minutes: int = 30


class TwoFactorEnableResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TwoFactorVerifyRequest(BaseModel):
    code: Optional[str] = None
    recovery_code: Optional[str] = None
    setup_confirm: bool = False


class TwoFactorDisableRequest(BaseModel):
    password: str
    code: Optional[str] = None
    recovery_code: Optional[str] = None


class IntegrationSecretUpdate(BaseModel):
    secret: str = Field(..., min_length=1, max_length=4096)


class UserListItem(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    plan_code: str
    subscription_status: Optional[str]
    projects_used: int
    projects_limit: int
    ai_used: int
    ai_limit: int
    is_active: bool
    last_login_at: Optional[datetime] = None


class SupportNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=20000)


class SupportNoteResponse(BaseModel):
    id: UUID
    body: str
    author_email: Optional[str] = None
    created_at: datetime


class StaffInviteCreate(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    role: str
    force_client_collision: bool = False


class StaffInviteAccept(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


class StaffRoleUpdate(BaseModel):
    role: str


class BlockUserBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class AdminSettingsPatch(BaseModel):
    team_2fa_required: Optional[bool] = None
    support_impersonation_allowed: Optional[bool] = None
    session_logging_enabled: Optional[bool] = None
    ip_whitelist_enabled: Optional[bool] = None
    ip_whitelist: Optional[List[str]] = None
    maintenance_mode: Optional[bool] = None
    registration_enabled: Optional[bool] = None
    team_email_alerts_enabled: Optional[bool] = None
    trial_days: Optional[int] = None
    openai_balance_usd: Optional[float] = None
    openai_alert_threshold_usd: Optional[float] = None


class SeoBlogPostCreate(BaseModel):
    slug: str
    title: str
    content_html: str = ""
    category: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[str] = None
    cover_url: Optional[str] = None
    traffic_monthly: int = 0


class SeoBlogPostUpdate(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    content_html: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: Optional[str] = None
    cover_url: Optional[str] = None
    traffic_monthly: Optional[int] = None


class SeoSitePageUpdate(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    title: Optional[str] = None
    traffic_monthly: Optional[int] = None
