from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Optional

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
    # Отдельная пара приложения VK Ads. Старые VK_CLIENT_* остаются fallback,
    # чтобы не ломать уже развёрнутые обычные OAuth-подключения.
    vk_ads_client_id: str
    vk_ads_client_secret: str
    vk_ads_oauth_scope: str
    # Вход на сайт через OAuth 2.1 VK ID (id.vk.ru). Если пусто — vk_client_id. Секрет для обмена кода не требуется (дока VK ID).
    vk_login_client_id: str
    vk_login_client_secret: str
    vk_login_scope: str
    vk_id_oauth_base: str
    max_bot_token: str
    max_bot_name: str
    max_webhook_secret: str
    max_reports_bot_token: str
    max_reports_bot_name: str
    max_reports_webhook_secret: str
    max_api_base: str
    max_login_ttl_seconds: int
    max_poll_interval_ms: int
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
    # Домен для синтетического email (VK и Яндекс без почты в ответе). Должен проходить проверку EmailStr.
    oauth_login_synthetic_email_domain: str


@dataclass
class PublicDomainConfig:
    admierra_deploy_env: str
    admierra_public_host: str
    frontend_url: str


@dataclass
class OpenAIConfig:
    api_key: str
    model: str
    base_url: str


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
    plan_start_max_staff: int
    plan_basic_max_staff: int
    plan_standard_max_staff: int
    plan_start_max_clients: int
    plan_basic_max_clients: int
    plan_standard_max_clients: int
    ai_period_days: int


@dataclass
class CloudPaymentsConfig:
    public_id: str
    api_secret: str
    currency: str
    webhook_secret: str
    # Параметры онлайн-чека (CloudKassir через CloudPayments receipt).
    receipt_taxation_system: int
    # НДС позиции: None = «без НДС» (УСН/патент), 0 = «НДС 0%» — для налоговой это
    # разные вещи, поэтому пустое значение переменной трактуем как None.
    receipt_vat: Optional[int]
    receipt_method: int
    receipt_object: int


@dataclass
class SmtpConfig:
    enabled: bool
    host: str
    port: int
    user: str
    password: str
    from_addr: str
    use_tls: bool


@dataclass
class UniSenderConfig:
    api_key: str
    from_email: str
    from_name: str
    api_url: str


@dataclass
class SupportConfig:
    """Куда слать обращения с формы «Предложить идею» (POST /api/support/idea)."""
    inbox_email: str


@dataclass
class TelegramBotConfig:
    """Тот же бот, что для lead_validator (TELEGRAM_BOT_TOKEN). Webhook — для привязки чата к пользователю."""
    bot_token: str
    webhook_secret: str
    bot_username: str  # без @; если пусто — username подтянется через getMe


@dataclass
class DetectorCfg:
    enabled: bool
    baseline_days: int
    fresh_window_days: int
    fresh_window_skip_days: int
    warmup_days: int
    min_conversions_silence: int
    min_conversions_warning_only: int
    duration_warning: int
    duration_problem: int
    recovery_days: int
    campaign_min_baseline_spend: float
    campaign_empty_spend_threshold: float
    campaign_majority_threshold: float
    thresholds_json: str
    holidays_json: str
    # Iteration 3 — plan/fact and critical failures.  Every product threshold
    # lives here so a calibration never requires a code deployment.
    plan_start_pause_days: int
    plan_spend_warning_deviation: float
    plan_spend_problem_deviation: float
    plan_min_expected_spend: float
    plan_exhausted_min_days_remaining: int
    plan_cpl_window_days: int
    plan_cpl_warning_ratio: float
    plan_cpl_problem_ratio: float
    plan_cpl_problem_target_multiplier: float
    plan_cpl_warning_target_multiplier: float
    plan_cpl_problem_budget_share: float
    plan_cpl_warning_budget_share: float
    plan_leads_warning_deviation: float
    plan_leads_problem_deviation: float
    plan_min_expected_leads: int
    balance_spend_window_days: int
    balance_warning_days: float
    balance_problem_days: float
    balance_zero_history_days: int
    stopped_spend_zero_days: int
    stopped_prior_spend_days: int
    stopped_min_daily_spend: float
    tracking_zero_leads_days: int
    tracking_min_clicks: int
    tracking_history_days: int
    tracking_history_active_days: int
    sync_stale_days: int
    campaign_cpl_problem_target_multiplier: float
    campaign_cpl_budget_share: float
    onboarding_dismiss_days: int
    # §4: сколько должна измениться второстепенная метрика (окно к окну),
    # чтобы диагностика посчитала это «вырос/упал», а не колебанием.
    diagnostic_change_threshold: float


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
    telegram_bot: TelegramBotConfig
    smtp: SmtpConfig
    unisender: UniSenderConfig
    support: SupportConfig
    detector: DetectorCfg


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
            vk_ads_client_id=_env("VK_ADS_CLIENT_ID") or _env("VK_CLIENT_ID"),
            vk_ads_client_secret=_env("VK_ADS_CLIENT_SECRET") or _env("VK_CLIENT_SECRET"),
            vk_ads_oauth_scope=getenv("VK_ADS_OAUTH_SCOPE", "read_ads,read_payments,create_ads"),
            vk_login_client_id=_env("VK_LOGIN_CLIENT_ID"),
            vk_login_client_secret=_env("VK_LOGIN_CLIENT_SECRET"),
            vk_login_scope=getenv("VK_LOGIN_SCOPE", "email"),
            # Пустое значение в .env не должно обнулять базовый URL (getenv с ключом ="" даёт "" без дефолта).
            vk_id_oauth_base=(_env("VK_ID_OAUTH_BASE") or "https://id.vk.ru").rstrip("/"),
            max_bot_token=_env("MAX_BOT_TOKEN"),
            max_bot_name=_env("MAX_BOT_NAME"),
            max_webhook_secret=_env("MAX_WEBHOOK_SECRET"),
            max_reports_bot_token=_env("MAX_REPORTS_BOT_TOKEN"),
            max_reports_bot_name=_env("MAX_REPORTS_BOT_NAME"),
            max_reports_webhook_secret=_env("MAX_REPORTS_WEBHOOK_SECRET"),
            max_api_base=(_env("MAX_API_BASE", "https://platform-api.max.ru") or "https://platform-api.max.ru").rstrip("/"),
            max_login_ttl_seconds=int(_env("MAX_LOGIN_TTL_SECONDS", "300")),
            max_poll_interval_ms=int(_env("MAX_POLL_INTERVAL_MS", "2000")),
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
            # Домен должен проходить EmailStr (не использовать .localhost — зарезервировано в pydantic-email-validator).
            oauth_login_synthetic_email_domain=_env(
                "OAUTH_LOGIN_SYNTHETIC_EMAIL_DOMAIN",
                "vk-oauth.admirra.ru",
            ),
        ),
        public_domain=PublicDomainConfig(
            admierra_deploy_env=_env("ADMIRRA_DEPLOY_ENV").lower(),
            admierra_public_host=_env("ADMIRRA_PUBLIC_HOST"),
            frontend_url=_env("FRONTEND_URL"),
        ),
        openai=OpenAIConfig(
            api_key=_env("OPENAI_API_KEY"),
            model=_env("OPENAI_MODEL", "claude-sonnet-4-6"),
            base_url=_env("OPENAI_BASE_URL", "https://api.proxyapi.ru/anthropic"),
        ),
        billing=BillingConfig(
            billing_enabled=_bool("BILLING_ENABLED", False),
            billing_env=_env("BILLING_ENV", "dev").lower(),
            billing_enforce_limits=_bool("BILLING_ENFORCE_LIMITS", False),
            billing_admin_whitelist=_env("BILLING_ADMIN_WHITELIST"),
            trial_days=int(_env("BILLING_TRIAL_DAYS", "14")),
            plan_start_price_rub=int(_env("BILLING_PLAN_START_PRICE_RUB", "1590")),
            plan_basic_price_rub=int(_env("BILLING_PLAN_BASIC_PRICE_RUB", "3990")),
            plan_standard_price_rub=int(_env("BILLING_PLAN_STANDARD_PRICE_RUB", "9990")),
            plan_start_max_projects=int(_env("BILLING_PLAN_START_MAX_PROJECTS", "1")),
            plan_basic_max_projects=int(_env("BILLING_PLAN_BASIC_MAX_PROJECTS", "5")),
            plan_standard_max_projects=int(_env("BILLING_PLAN_STANDARD_MAX_PROJECTS", "30")),
            plan_start_ai_limit=int(_env("BILLING_PLAN_START_AI_LIMIT", "30")),
            plan_basic_ai_limit=int(_env("BILLING_PLAN_BASIC_AI_LIMIT", "100")),
            plan_standard_ai_limit=int(_env("BILLING_PLAN_STANDARD_AI_LIMIT", "450")),
            plan_start_max_staff=int(_env("BILLING_PLAN_START_MAX_STAFF", "1")),
            plan_basic_max_staff=int(_env("BILLING_PLAN_BASIC_MAX_STAFF", "5")),
            plan_standard_max_staff=int(_env("BILLING_PLAN_STANDARD_MAX_STAFF", "10")),
            plan_start_max_clients=int(_env("BILLING_PLAN_START_MAX_CLIENTS", "0")),
            plan_basic_max_clients=int(_env("BILLING_PLAN_BASIC_MAX_CLIENTS", "10")),
            plan_standard_max_clients=int(_env("BILLING_PLAN_STANDARD_MAX_CLIENTS", "-1")),
            ai_period_days=int(_env("BILLING_AI_PERIOD_DAYS", "30")),
        ),
        cloudpayments=CloudPaymentsConfig(
            public_id=_env("CLOUDPAYMENTS_PUBLIC_ID"),
            api_secret=_env("CLOUDPAYMENTS_API_SECRET"),
            currency=_env("CLOUDPAYMENTS_CURRENCY", "RUB"),
            webhook_secret=_env("CLOUDPAYMENTS_WEBHOOK_SECRET"),
            receipt_taxation_system=int(_env("CLOUDPAYMENTS_RECEIPT_TAXATION_SYSTEM", "0")),
            # Пусто/none = «без НДС» (null в чеке); число = ставка (0 = «НДС 0%», 20 и т.д.)
            receipt_vat=(
                int(_env("CLOUDPAYMENTS_RECEIPT_VAT"))
                if _env("CLOUDPAYMENTS_RECEIPT_VAT", "").strip().lower() not in ("", "none", "null")
                else None
            ),
            receipt_method=int(_env("CLOUDPAYMENTS_RECEIPT_METHOD", "0")),
            receipt_object=int(_env("CLOUDPAYMENTS_RECEIPT_OBJECT", "4")),
        ),
        telegram_bot=TelegramBotConfig(
            bot_token=_env("TELEGRAM_BOT_TOKEN"),
            webhook_secret=_env("TELEGRAM_WEBHOOK_SECRET"),
            bot_username=_env("TELEGRAM_BOT_USERNAME"),
        ),
        smtp=SmtpConfig(
            enabled=_bool("SMTP_ENABLED", False),
            host=_env("SMTP_HOST"),
            port=int(_env("SMTP_PORT", "587")),
            user=_env("SMTP_USER"),
            password=_env("SMTP_PASSWORD"),
            from_addr=_env("SMTP_FROM", "noreply@admirra.ru"),
            use_tls=_bool("SMTP_USE_TLS", True),
        ),
        unisender=UniSenderConfig(
            api_key=_env("UNISENDER_API_KEY"),
            from_email=_env("UNISENDER_FROM_EMAIL", "reports@admirra.online"),
            from_name=_env("UNISENDER_FROM_NAME", "AdMirra"),
            api_url=_env("UNISENDER_API_URL", "https://go2.unisender.ru/ru/transactional/api/v1"),
        ),
        support=SupportConfig(
            inbox_email=_env("SUPPORT_INBOX_EMAIL", "support@admirra.ru"),
        ),
        detector=DetectorCfg(
            enabled=_bool("DETECTOR_ENABLED", True),
            baseline_days=int(_env("DETECTOR_BASELINE_DAYS", "42")),
            fresh_window_days=int(_env("DETECTOR_FRESH_WINDOW_DAYS", "7")),
            fresh_window_skip_days=int(_env("DETECTOR_FRESH_WINDOW_SKIP_DAYS", "2")),
            warmup_days=int(_env("DETECTOR_WARMUP_DAYS", "21")),
            min_conversions_silence=int(_env("DETECTOR_MIN_CONVERSIONS_SILENCE", "10")),
            min_conversions_warning_only=int(_env("DETECTOR_MIN_CONVERSIONS_WARNING_ONLY", "30")),
            duration_warning=int(_env("DETECTOR_DURATION_WARNING", "2")),
            duration_problem=int(_env("DETECTOR_DURATION_PROBLEM", "3")),
            recovery_days=int(_env("DETECTOR_RECOVERY_DAYS", "2")),
            campaign_min_baseline_spend=float(_env("DETECTOR_CAMPAIGN_MIN_BASELINE_SPEND", "500")),
            campaign_empty_spend_threshold=float(_env("DETECTOR_CAMPAIGN_EMPTY_SPEND_THRESHOLD", "3000")),
            campaign_majority_threshold=float(_env("DETECTOR_CAMPAIGN_MAJORITY_THRESHOLD", "0.5")),
            thresholds_json=_env("DETECTOR_THRESHOLDS_JSON"),
            holidays_json=_env("DETECTOR_HOLIDAYS_JSON"),
            plan_start_pause_days=int(_env("DETECTOR_PLAN_START_PAUSE_DAYS", "3")),
            plan_spend_warning_deviation=float(_env("DETECTOR_PLAN_SPEND_WARNING_DEVIATION", "0.20")),
            plan_spend_problem_deviation=float(_env("DETECTOR_PLAN_SPEND_PROBLEM_DEVIATION", "0.40")),
            plan_min_expected_spend=float(_env("DETECTOR_PLAN_MIN_EXPECTED_SPEND", "1000")),
            plan_exhausted_min_days_remaining=int(_env("DETECTOR_PLAN_EXHAUSTED_MIN_DAYS_REMAINING", "2")),
            plan_cpl_window_days=int(_env("DETECTOR_PLAN_CPL_WINDOW_DAYS", "7")),
            plan_cpl_warning_ratio=float(_env("DETECTOR_PLAN_CPL_WARNING_RATIO", "1.3")),
            plan_cpl_problem_ratio=float(_env("DETECTOR_PLAN_CPL_PROBLEM_RATIO", "1.8")),
            plan_cpl_problem_target_multiplier=float(_env("DETECTOR_PLAN_CPL_PROBLEM_TARGET_MULTIPLIER", "5")),
            plan_cpl_warning_target_multiplier=float(_env("DETECTOR_PLAN_CPL_WARNING_TARGET_MULTIPLIER", "10")),
            plan_cpl_problem_budget_share=float(_env("DETECTOR_PLAN_CPL_PROBLEM_BUDGET_SHARE", "0.15")),
            plan_cpl_warning_budget_share=float(_env("DETECTOR_PLAN_CPL_WARNING_BUDGET_SHARE", "0.30")),
            plan_leads_warning_deviation=float(_env("DETECTOR_PLAN_LEADS_WARNING_DEVIATION", "0.20")),
            plan_leads_problem_deviation=float(_env("DETECTOR_PLAN_LEADS_PROBLEM_DEVIATION", "0.40")),
            plan_min_expected_leads=int(_env("DETECTOR_PLAN_MIN_EXPECTED_LEADS", "10")),
            balance_spend_window_days=int(_env("DETECTOR_BALANCE_SPEND_WINDOW_DAYS", "7")),
            balance_warning_days=float(_env("DETECTOR_BALANCE_WARNING_DAYS", "3")),
            balance_problem_days=float(_env("DETECTOR_BALANCE_PROBLEM_DAYS", "1")),
            balance_zero_history_days=int(_env("DETECTOR_BALANCE_ZERO_HISTORY_DAYS", "7")),
            stopped_spend_zero_days=int(_env("DETECTOR_STOPPED_SPEND_ZERO_DAYS", "2")),
            stopped_prior_spend_days=int(_env("DETECTOR_STOPPED_PRIOR_SPEND_DAYS", "7")),
            stopped_min_daily_spend=float(_env("DETECTOR_STOPPED_MIN_DAILY_SPEND", "200")),
            tracking_zero_leads_days=int(_env("DETECTOR_TRACKING_ZERO_LEADS_DAYS", "3")),
            tracking_min_clicks=int(_env("DETECTOR_TRACKING_MIN_CLICKS", "100")),
            tracking_history_days=int(_env("DETECTOR_TRACKING_HISTORY_DAYS", "14")),
            tracking_history_active_days=int(_env("DETECTOR_TRACKING_HISTORY_ACTIVE_DAYS", "10")),
            sync_stale_days=int(_env("DETECTOR_SYNC_STALE_DAYS", "2")),
            campaign_cpl_problem_target_multiplier=float(_env("DETECTOR_CAMPAIGN_CPL_TARGET_MULTIPLIER", "3")),
            campaign_cpl_budget_share=float(_env("DETECTOR_CAMPAIGN_CPL_BUDGET_SHARE", "0.10")),
            onboarding_dismiss_days=int(_env("DETECTOR_ONBOARDING_DISMISS_DAYS", "30")),
            diagnostic_change_threshold=float(_env("DETECTOR_DIAGNOSTIC_CHANGE_THRESHOLD", "0.20")),
        ),
    )

