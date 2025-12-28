import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Numeric, Date, Enum, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True) # Temporarily nullable for migration
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.MANAGER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    clients = relationship("Client", back_populates="owner")

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String, nullable=False)
    description = Column(String)
    spreadsheet_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="clients")
    integrations = relationship("Integration", back_populates="client")
    yandex_stats = relationship("YandexStats", back_populates="client")
    yandex_keywords = relationship("YandexKeywords", back_populates="client")
    yandex_groups = relationship("YandexGroups", back_populates="client")
    vk_stats = relationship("VKStats", back_populates="client")
    weekly_reports = relationship("WeeklyReport", back_populates="client")
    monthly_reports = relationship("MonthlyReport", back_populates="client")

class IntegrationPlatform(enum.Enum):
    YANDEX_DIRECT = "YANDEX_DIRECT"
    VK_ADS = "VK_ADS"
    YANDEX_METRIKA = "YANDEX_METRIKA"

class IntegrationSyncStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    NEVER = "NEVER"

class Integration(Base):
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    platform = Column(Enum(IntegrationPlatform), nullable=False)
    access_token = Column(String, nullable=False) # Should be encrypted in production
    refresh_token = Column(String)
    expires_at = Column(DateTime)
    account_id = Column(String) # Logic ID in the platform
    sync_status = Column(Enum(IntegrationSyncStatus), default=IntegrationSyncStatus.NEVER)
    last_sync_at = Column(DateTime)
    error_message = Column(String)

    client = relationship("Client", back_populates="integrations")

class YandexStats(Base):
    __tablename__ = "yandex_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(Integer, default=0)
    ctr = Column(Numeric(10, 4))
    cpc = Column(Numeric(20, 2))

    client = relationship("Client", back_populates="yandex_stats")

class YandexKeywords(Base):
    __tablename__ = "yandex_keywords"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    keyword = Column(String)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(Integer, default=0)

    client = relationship("Client", back_populates="yandex_keywords")

class YandexGroups(Base):
    __tablename__ = "yandex_groups"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_name = Column(String)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(Integer, default=0)

    client = relationship("Client", back_populates="yandex_groups")

class VKStats(Base):
    __tablename__ = "vk_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), index=True)
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(Integer, default=0)

    client = relationship("Client", back_populates="vk_stats")

class MetrikaGoals(Base):
    __tablename__ = "metrika_goals"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    date = Column(Date, index=True, nullable=False)
    goal_id = Column(String, nullable=False)
    goal_name = Column(String)
    conversion_count = Column(Integer, default=0)

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
