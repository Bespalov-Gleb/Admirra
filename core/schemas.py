from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

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

from core import models

# Integration Schemas
class IntegrationBase(BaseModel):
    platform: models.IntegrationPlatform
    account_id: Optional[str] = None

    @field_validator('platform', mode='before')
    @classmethod
    def normalize_platform(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

class IntegrationCreate(IntegrationBase):
    access_token: Optional[str] = None # Optional now because VK might use client_id/secret instead
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    client_name: str # To create a client if needed

class IntegrationResponse(IntegrationBase):
    id: UUID
    client_id: UUID
    access_token: str
    
    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

# Stats Schemas
class StatsSummary(BaseModel):
    expenses: float
    impressions: int
    clicks: int
    leads: int
    cpc: float
    cpa: float

class DynamicsStat(BaseModel):
    labels: List[str]
    costs: List[float]
    clicks: List[int]

class CampaignStat(BaseModel):
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
    name: str
    count: int
    trend: float

class IntegrationStatus(BaseModel):
    platform: str
    is_connected: bool

class SyncRequest(BaseModel):
    days: int = 7

# Error Schema
class ErrorResponse(BaseModel):
    detail: str
