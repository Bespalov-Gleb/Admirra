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
    # Пользовательский FinanceToken для Яндекс.Директа (или его база)
    # Используется при запросе баланса через AccountManagement API.
    yandex_finance_token = Column(String, nullable=True)

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
    MYTARGET = "MYTARGET"

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
    platform_client_id = Column(String) # For platforms like VK Ads
    platform_client_secret = Column(String) # For platforms like VK Ads
    expires_at = Column(DateTime)
    account_id = Column(String) # Logic ID in the platform
    sync_status = Column(Enum(IntegrationSyncStatus), default=IntegrationSyncStatus.NEVER)
    last_sync_at = Column(DateTime)
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
    
    # Balance Support
    balance = Column(Numeric(10, 2), nullable=True) # Account balance in platform currency
    currency = Column(String(3), default="RUB") # Currency code (RUB, USD, EUR, etc.)

    client = relationship("Client", back_populates="integrations")
    campaigns = relationship("Campaign", back_populates="integration", cascade="all, delete-orphan")

    @property
    def client_name(self):
        """Property to expose client name for API responses."""
        return self.client.name if self.client else None

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    external_id = Column(String, nullable=False) # Campaign ID from the platform
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    integration = relationship("Integration", back_populates="campaigns")
    yandex_stats = relationship("YandexStats", back_populates="campaign")
    vk_stats = relationship("VKStats", back_populates="campaign")

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
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    date = Column(Date, index=True, nullable=False)
    campaign_name = Column(String)
    group_name = Column(String)
    impressions = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    cost = Column(Numeric(20, 2), default=0)
    conversions = Column(BigInteger, default=0)

    client = relationship("Client", back_populates="yandex_groups")

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
    conversions = Column(BigInteger, default=0)

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
    enable_gosuslugi_check = Column(Boolean, default=False)  # Проверка Госуслуг
    enable_metrica_export = Column(Boolean, default=True)  # Отправка в Яндекс.Метрику
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    client = relationship("Client", foreign_keys=[client_id])
    leads = relationship("Lead", back_populates="project", cascade="all, delete-orphan")


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
    has_tiktok = Column(Boolean, nullable=True)  # TT
    has_vk = Column(Boolean, nullable=True)  # BK
    social_accounts_data = Column(String, nullable=True)  # JSON с данными аккаунтов
    
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
