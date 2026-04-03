from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class SecurityConfig:
    secret_key: str
    encryption_key: str


@dataclass
class DatabaseConfig:
    url: str


@dataclass
class OAuthConfig:
    yandex_client_id: str
    yandex_client_secret: str
    vk_client_id: str
    vk_client_secret: str
    vk_ads_oauth_scope: str
    mytarget_client_id: str
    mytarget_client_secret: str
    mytarget_auth_url: str
    mytarget_token_url: str
    yandex_auth_url: str
    yandex_token_url: str


@dataclass
class AuthConfig:
    resend_cooldown_sec: int
    auth_login_otp_enabled: bool
    auth_require_email_verified: bool


@dataclass
class PublicDomainConfig:
    admierra_deploy_env: str
    admierra_public_host: str
    frontend_url: str


@dataclass
class OpenAIConfig:
    api_key: str
    model: str


@dataclass
class BillingConfig:
    billing_enabled: bool
    billing_env: str
    billing_enforce_limits: bool
    billing_admin_whitelist: str
    trial_days: int
    plan_start_price_rub: int
    plan_basic_price_rub: int
    plan_standard_price_rub: int
    plan_start_max_projects: int
    plan_basic_max_projects: int
    plan_standard_max_projects: int
    plan_start_ai_limit: int
    plan_basic_ai_limit: int
    plan_standard_ai_limit: int
    ai_period_days: int


@dataclass
class CloudPaymentsConfig:
    public_id: str
    api_secret: str
    currency: str
    webhook_secret: str


@dataclass
class Config:
    security: SecurityConfig
    database: DatabaseConfig
    oauth: OAuthConfig
    auth: AuthConfig
    public_domain: PublicDomainConfig
    openai: OpenAIConfig
    billing: BillingConfig
    cloudpayments: CloudPaymentsConfig


def _bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env(name: str, default: str = "") -> str:
    return (getenv(name) or default).strip()


@lru_cache(maxsize=1)
def get_config() -> Config:
    project_root = Path(__file__).resolve().parent.parent
    app_env = (getenv("APP_ENV") or "").strip()
    if app_env:
        load_dotenv(project_root / f".env.{app_env}", override=False)
    load_dotenv(project_root / ".env", override=False)

    return Config(
        security=SecurityConfig(
            secret_key=_env("SECRET_KEY"),
            encryption_key=_env("ENCRYPTION_KEY"),
        ),
        database=DatabaseConfig(
            url=_env("DATABASE_URL"),
        ),
        oauth=OAuthConfig(
            yandex_client_id=_env("YANDEX_CLIENT_ID"),
            yandex_client_secret=_env("YANDEX_CLIENT_SECRET"),
            vk_client_id=_env("VK_CLIENT_ID"),
            vk_client_secret=_env("VK_CLIENT_SECRET"),
            vk_ads_oauth_scope=getenv("VK_ADS_OAUTH_SCOPE", "read_ads,read_payments,create_ads"),
            mytarget_client_id=_env("MYTARGET_CLIENT_ID"),
            mytarget_client_secret=_env("MYTARGET_CLIENT_SECRET"),
            mytarget_auth_url=getenv("MYTARGET_AUTH_URL", "https://target-sandbox.my.com/api/v2/oauth2/authorize"),
            mytarget_token_url=getenv("MYTARGET_TOKEN_URL", "https://target-sandbox.my.com/api/v2/oauth2/token.json"),
            yandex_auth_url="https://oauth.yandex.ru/authorize",
            yandex_token_url="https://oauth.yandex.ru/token",
        ),
        auth=AuthConfig(
            resend_cooldown_sec=int(getenv("AUTH_RESEND_COOLDOWN_SEC", "60")),
            auth_login_otp_enabled=_bool("AUTH_LOGIN_OTP_ENABLED", True),
            auth_require_email_verified=_bool("AUTH_REQUIRE_EMAIL_VERIFIED", True),
        ),
        public_domain=PublicDomainConfig(
            admierra_deploy_env=_env("ADMIRRA_DEPLOY_ENV").lower(),
            admierra_public_host=_env("ADMIRRA_PUBLIC_HOST"),
            frontend_url=_env("FRONTEND_URL"),
        ),
        openai=OpenAIConfig(
            api_key=_env("OPENAI_API_KEY"),
            model=_env("OPENAI_MODEL", "gpt-4o-mini"),
        ),
        billing=BillingConfig(
            billing_enabled=_bool("BILLING_ENABLED", False),
            billing_env=_env("BILLING_ENV", "dev").lower(),
            billing_enforce_limits=_bool("BILLING_ENFORCE_LIMITS", False),
            billing_admin_whitelist=_env("BILLING_ADMIN_WHITELIST"),
            trial_days=int(_env("BILLING_TRIAL_DAYS", "14")),
            plan_start_price_rub=int(_env("BILLING_PLAN_START_PRICE_RUB", "1590")),
            plan_basic_price_rub=int(_env("BILLING_PLAN_BASIC_PRICE_RUB", "3990")),
            plan_standard_price_rub=int(_env("BILLING_PLAN_STANDARD_PRICE_RUB", "9900")),
            plan_start_max_projects=int(_env("BILLING_PLAN_START_MAX_PROJECTS", "1")),
            plan_basic_max_projects=int(_env("BILLING_PLAN_BASIC_MAX_PROJECTS", "5")),
            plan_standard_max_projects=int(_env("BILLING_PLAN_STANDARD_MAX_PROJECTS", "15")),
            plan_start_ai_limit=int(_env("BILLING_PLAN_START_AI_LIMIT", "30")),
            plan_basic_ai_limit=int(_env("BILLING_PLAN_BASIC_AI_LIMIT", "100")),
            plan_standard_ai_limit=int(_env("BILLING_PLAN_STANDARD_AI_LIMIT", "300")),
            ai_period_days=int(_env("BILLING_AI_PERIOD_DAYS", "30")),
        ),
        cloudpayments=CloudPaymentsConfig(
            public_id=_env("CLOUDPAYMENTS_PUBLIC_ID"),
            api_secret=_env("CLOUDPAYMENTS_API_SECRET"),
            currency=_env("CLOUDPAYMENTS_CURRENCY", "RUB"),
            webhook_secret=_env("CLOUDPAYMENTS_WEBHOOK_SECRET"),
        ),
    )

