from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
import json

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # Пользовательский FinanceToken для Яндекс.Директа (или его база)
    yandex_finance_token: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenData(BaseModel):
    email: Optional[str] = None


class UserUpdateSettings(BaseModel):
    """
    Обновление настроек текущего пользователя.
    Пока даём редактировать только безопасные поля (имя, фамилия, FinanceToken).
    """
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    yandex_finance_token: Optional[str] = None

from core import models

# Integration Schemas
class IntegrationBase(BaseModel):
    platform: models.IntegrationPlatform
    account_id: Optional[str] = None
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
    access_token: str
    selected_goals: Optional[List[str]] = None
    primary_goal_id: Optional[str] = None
    campaigns: List["CampaignResponse"] = []
    
    class Config:
        from_attributes = True

# Campaign Schemas
class CampaignBase(BaseModel):
    external_id: str
    name: str
    is_active: bool = True

class CampaignCreate(CampaignBase):
    integration_id: UUID

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    client_id: Optional[UUID] = None # For moving campaign between projects (effectively changing integration/client)

class CampaignResponse(CampaignBase):
    id: UUID
    integration_id: UUID
    
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

class ClientResponse(ClientBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    integrations: List[IntegrationResponse] = []
    summary: Optional[StatsSummary] = None

    class Config:
        from_attributes = True



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

class IntegrationStatus(BaseModel):
    platform: str
    is_connected: bool

class SyncRequest(BaseModel):
    days: int = 7

# Error Schema
class ErrorResponse(BaseModel):
    detail: str
