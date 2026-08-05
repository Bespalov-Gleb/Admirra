from typing import Optional
from pathlib import Path
import logging
import time
import uuid
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse # Changed from fastapi.responses.FileResponse
from core.database import engine
from core import models
from sqlalchemy import text
import os
from dotenv import load_dotenv

# Load .env file for local development (Docker Compose loads it automatically)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("api")

# Enable automatic table creation with retry logic
def init_db_with_retry(max_retries=10, retry_delay=2):
    """
    Initialize database with retry logic to handle cases when DB is not ready yet.
    """
    from sqlalchemy.exc import OperationalError
    
    for attempt in range(max_retries):
        try:
            models.Base.metadata.create_all(bind=engine)
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_updated_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS interface_language VARCHAR(8) NOT NULL DEFAULT 'ru'"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_email VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS metrika_client_id VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS metrika_yclid VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ym_milestones TEXT"))
                # username — отображаемое имя, может повторяться (логин по email).
                # Снимаем устаревшее UNIQUE-ограничение, оставляем обычный индекс.
                conn.execute(text("DROP INDEX IF EXISTS ix_users_username"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS direction_label VARCHAR(32) NOT NULL DEFAULT 'directions'"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS folder_id UUID REFERENCES folders(id) ON DELETE SET NULL"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_ai_comment TEXT"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_ai_comment_at TIMESTAMP"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS ai_comment_cache JSONB"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS directions_budget_mode VARCHAR(16) NOT NULL DEFAULT 'fixed'"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS strategy_context TEXT"))
                # §9.2 экономики: модель тёплых проектов и дельта с последнего захода.
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_dashboard_viewed_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_comment_generated_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS bid_strategy VARCHAR"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comparability_events (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                        type VARCHAR(32) NOT NULL,
                        event_date DATE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comparability_events_client ON comparability_events (client_id, event_date)"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ai_comment_generations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                        period_from DATE,
                        period_to DATE,
                        generated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                        trigger VARCHAR(24),
                        text TEXT,
                        fingerprint VARCHAR(32),
                        prompt_version VARCHAR(16),
                        model VARCHAR(64),
                        directions_mode VARCHAR(16),
                        vat_mode VARCHAR(16),
                        context_hash VARCHAR(32),
                        rating SMALLINT,
                        rated_by UUID,
                        rated_at TIMESTAMP WITH TIME ZONE
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_comment_gen_client ON ai_comment_generations (client_id, generated_at DESC)"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS rating SMALLINT"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clients_folder_id ON clients (folder_id)"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS platform_status VARCHAR"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS platform_state VARCHAR"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS display_status VARCHAR"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS status_synced_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS utm_source VARCHAR"))
                # Отдельный OAuth-грант Метрики для Avito (правка 10). Схема на проде
                # применяется этими ALTER'ами, а не alembic — иначе колонок нет.
                conn.execute(text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS metrika_access_token VARCHAR"))
                conn.execute(text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS metrika_refresh_token VARCHAR"))
                conn.execute(text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS metrika_account_id VARCHAR"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS billing_period VARCHAR"))
                conn.execute(text("ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS sections VARCHAR"))
                conn.execute(text("ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS chart_metrics VARCHAR"))
                conn.execute(text("ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS dynamics_metrics VARCHAR"))
                conn.execute(text("ALTER TABLE report_schedules ADD COLUMN IF NOT EXISTS chat_targets VARCHAR"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS card_last4 VARCHAR"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS card_type VARCHAR"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS card_exp VARCHAR"))
                conn.execute(text("ALTER TABLE yandex_keywords ADD COLUMN IF NOT EXISTS campaign_id UUID"))
                conn.execute(text("ALTER TABLE yandex_groups ADD COLUMN IF NOT EXISTS campaign_id UUID"))
                conn.execute(text("ALTER TABLE yandex_groups ADD COLUMN IF NOT EXISTS group_id VARCHAR"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_groups_client_id ON yandex_groups (client_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_groups_campaign_id ON yandex_groups (campaign_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_groups_group_id ON yandex_groups (group_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_ads_client_id ON yandex_ads (client_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_ads_campaign_id ON yandex_ads (campaign_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_ads_group_id ON yandex_ads (group_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_yandex_ads_ad_id ON yandex_ads (ad_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_groups_client_id ON avito_groups (client_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_groups_campaign_id ON avito_groups (campaign_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_groups_group_id ON avito_groups (group_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_creatives_client_id ON avito_creatives (client_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_creatives_campaign_id ON avito_creatives (campaign_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_creatives_group_id ON avito_creatives (group_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_avito_creatives_creative_id ON avito_creatives (creative_id)"))
                conn.execute(text("ALTER TABLE detector_alerts ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE detector_alerts ADD COLUMN IF NOT EXISTS snooze_source JSON"))
                conn.execute(text("ALTER TABLE detector_alerts ADD COLUMN IF NOT EXISTS not_problem_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_detector_alerts_snoozed_until ON detector_alerts (snoozed_until)"))
                # Детектор ит.4 (§9.1, §9.3): персональное «увидел» и дата захода.
                # Дубль миграции cc3d4e5f6a7b — новые таблицы create_all() создаёт,
                # но держим явные CREATE IF NOT EXISTS ради пересоздаваемой базы.
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS detector_alert_views (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        alert_id UUID NOT NULL REFERENCES detector_alerts(id) ON DELETE CASCADE,
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        seen_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                        seen_severity VARCHAR(16),
                        seen_deviation_pct NUMERIC(8, 2),
                        seen_actual_value NUMERIC(20, 2),
                        seen_baseline_value NUMERIC(20, 2),
                        acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
                        CONSTRAINT uq_detector_alert_view UNIQUE (alert_id, user_id)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_detector_alert_views_alert_id ON detector_alert_views (alert_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_detector_alert_views_user_id ON detector_alert_views (user_id)"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS detector_project_visits (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                        last_viewed_at TIMESTAMP WITH TIME ZONE,
                        previous_viewed_at TIMESTAMP WITH TIME ZONE,
                        CONSTRAINT uq_detector_project_visit UNIQUE (user_id, client_id)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_detector_project_visits_user_id ON detector_project_visits (user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_detector_project_visits_client_id ON detector_project_visits (client_id)"))
                # Индексы под горячие пути чтения/записи. Дубль миграции
                # v3w4x5y6z7a8: индексы, объявленные только в alembic, пропадают
                # при пересоздании базы через create_all() — проверено на проде,
                # где 7 таких индексов физически отсутствовали.
                for _idx_sql in (
                    "CREATE INDEX IF NOT EXISTS ix_yandex_stats_client_date_campaign ON yandex_stats (client_id, date, campaign_id)",
                    "CREATE INDEX IF NOT EXISTS ix_vk_stats_client_date_campaign ON vk_stats (client_id, date, campaign_id)",
                    "CREATE INDEX IF NOT EXISTS ix_avito_stats_client_date_campaign ON avito_stats (client_id, date, campaign_id)",
                    "CREATE INDEX IF NOT EXISTS ix_metrika_goals_client_date_goal ON metrika_goals (client_id, date, goal_id)",
                    "CREATE INDEX IF NOT EXISTS ix_metrika_goals_integration_date ON metrika_goals (integration_id, date)",
                    "CREATE INDEX IF NOT EXISTS ix_yandex_stats_campaign_id ON yandex_stats (campaign_id)",
                    "CREATE INDEX IF NOT EXISTS ix_vk_stats_campaign_id ON vk_stats (campaign_id)",
                    "CREATE INDEX IF NOT EXISTS ix_yandex_keywords_lookup ON yandex_keywords (client_id, date, campaign_name, keyword)",
                    "CREATE INDEX IF NOT EXISTS ix_yandex_groups_lookup ON yandex_groups (client_id, campaign_id, date, group_id)",
                    "CREATE INDEX IF NOT EXISTS ix_campaigns_integration_external ON campaigns (integration_id, external_id)",
                    "CREATE INDEX IF NOT EXISTS ix_sync_jobs_status_created ON sync_jobs (status, created_at)",
                    "CREATE INDEX IF NOT EXISTS ix_detector_alerts_client_status ON detector_alerts (client_id, status)",
                    "CREATE INDEX IF NOT EXISTS ix_detector_alerts_owner_status ON detector_alerts (owner_id, status)",
                    "CREATE INDEX IF NOT EXISTS ix_project_directions_client_position ON project_directions (client_id, position)",
                ):
                    conn.execute(text(_idx_sql))
                # Журнал денежных событий и отложенное понижение тарифа.
                # Дубль миграции w4x5y6z7a8b9 — см. комментарий про create_all выше.
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_plan_code VARCHAR"))
                # §7.2 экономики: версия прайс-бука, зафиксированная за аккаунтом.
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS price_book_version INTEGER"))
                # §8 экономики: докупленные слоты и состояние превышения лимита.
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS purchased_project_slots INTEGER NOT NULL DEFAULT 0"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS overflow_since TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS overflow_periods_count INTEGER NOT NULL DEFAULT 0"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_billing_period VARCHAR"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_purchased_project_slots INTEGER"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS price_book_snapshot JSON"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_price_book_snapshot JSON"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS overflow_notice_dismissed_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS recurring_sync_required BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS peak_active_projects INTEGER NOT NULL DEFAULT 0"))
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS overflow_warning_period_end TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_dashboard_snapshot JSON"))
                conn.execute(text("ALTER TABLE clients ADD COLUMN IF NOT EXISTS ai_comment_memory JSON"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS input_tokens INTEGER"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS output_tokens INTEGER"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS cache_creation_input_tokens INTEGER"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS cache_read_input_tokens INTEGER"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(14, 6)"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS cost_rub NUMERIC(14, 6)"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS duration_ms INTEGER"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS campaign_count INTEGER"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS attempt INTEGER NOT NULL DEFAULT 1"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS validation_failed BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.execute(text("ALTER TABLE ai_comment_generations ADD COLUMN IF NOT EXISTS viewed_at TIMESTAMP WITH TIME ZONE"))
                # §7.3: переименование кодов тарифов старой линейки в новую. Резолвер
                # понимает и старые коды (алиасы), но в БД приводим к канону, чтобы не
                # держать оба навсегда. Идемпотентно: повторный прогон ничего не меняет.
                conn.execute(text("UPDATE subscriptions SET plan_code='agency' WHERE plan_code='basic'"))
                conn.execute(text("UPDATE subscriptions SET plan_code='pro' WHERE plan_code='standard'"))
                conn.execute(text("UPDATE subscriptions SET pending_plan_code='agency' WHERE pending_plan_code='basic'"))
                conn.execute(text("UPDATE subscriptions SET pending_plan_code='pro' WHERE pending_plan_code='standard'"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS billing_events (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
                        event_type VARCHAR(16) NOT NULL,
                        invoice_id VARCHAR(64),
                        transaction_id VARCHAR(64),
                        cp_subscription_id VARCHAR(64),
                        amount NUMERIC(14, 2),
                        currency VARCHAR(8),
                        plan_code VARCHAR(32),
                        billing_period VARCHAR(8),
                        payload JSON,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                    )
                """))
                for _be_sql in (
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_user_id ON billing_events (user_id)",
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_subscription_id ON billing_events (subscription_id)",
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_event_type ON billing_events (event_type)",
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_invoice_id ON billing_events (invoice_id)",
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_cp_subscription_id ON billing_events (cp_subscription_id)",
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_created_at ON billing_events (created_at)",
                    "CREATE INDEX IF NOT EXISTS ix_billing_events_user_created ON billing_events (user_id, created_at)",
                    # Ключ идемпотентности вебхуков CloudPayments.
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_events_transaction "
                    "ON billing_events (transaction_id) WHERE transaction_id IS NOT NULL",
                ):
                    conn.execute(text(_be_sql))

                # ── Схема админ-панели (internal_admin). На проде уже применена
                # прошлым деплоем ru2online — все ALTER'ы идемпотентны (IF NOT
                # EXISTS), тут это no-op; на свежей БД create_all + эти ALTER'ы
                # создают колонки users и значения enum. Таблицы ia_* создаёт
                # create_all из internal_admin.models.
                for _role_val in ("SUPERADMIN", "STAFF_MANAGER", "SUPPORT", "SEO", "DEVELOPER"):
                    conn.execute(text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{_role_val}'"))
                conn.execute(text("""
                    DO $$ BEGIN
                        CREATE TYPE staffstatus AS ENUM ('PENDING','ACTIVE','INACTIVE');
                    EXCEPTION WHEN duplicate_object THEN null;
                    END $$;
                """))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_utm_source VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_utm_medium VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS registration_utm_campaign VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS block_reason VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_quota_resets_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_status staffstatus"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_totp_enabled BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_totp_secret_encrypted VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_totp_pending_secret_encrypted VARCHAR"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_recovery_codes_hashed JSONB"))
            logger.info("Database tables created successfully")
            return
        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise

init_db_with_retry()

# Fix for bcrypt 4.0.0+ and passlib compatibility
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (object,), {"__version__": bcrypt.__version__})

import mimetypes
mimetypes.add_type('application/javascript', '.js')

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend_api.auth import router as auth_router
from backend_api.oauth_login import router as oauth_login_router
from backend_api.telegram_report_link import link_router as telegram_link_router, webhook_router as telegram_webhook_router
from backend_api.max_report_link import link_router as max_reports_link_router, webhook_router as max_reports_webhook_router
from backend_api.integrations import router as integrations_router
from backend_api.stats import router as stats_router
from backend_api.clients import router as clients_router
from backend_api.folders import router as folders_router
from backend_api.directions import router as directions_router
from backend_api.campaigns import router as campaigns_router
from backend_api.phone_projects import router as phone_projects_router
from backend_api.phone_leads import router as phone_leads_router
from backend_api.phone_stats import router as phone_stats_router
from backend_api.billing import router as billing_router
from backend_api.notifications import router as notifications_router
from backend_api.support import router as support_router
from backend_api.health_routes import router as health_router
from backend_api.team import router as team_router
from backend_api.history import router as history_router
from internal_admin.router import router as internal_admin_router
from internal_admin.manager_router import router as internal_manager_router
from internal_admin.seo_router import router as internal_seo_router
from internal_admin.auth_public_router import router as internal_auth_public_router
import internal_admin.models  # noqa: F401 — регистрация ORM для create_all (таблицы ia_*)
from backend_api.detector import router as detector_router
from backend_api.brand import router as brand_router

try:
    from ai.router import router as ai_router
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    from backend_api.reports.router import router as reports_router
    REPORTS_AVAILABLE = True
except ImportError:
    REPORTS_AVAILABLE = False

# Lead Validator routers (публичные webhook'и и защищённые эндпоинты)
try:
    from lead_validator.router import router as lead_validator_router
    from lead_validator.webhook_router import router as webhook_router
    from lead_validator.tasks.alert_scheduler import run_daily_alerts, run_weekly_report
    LEAD_VALIDATOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Lead Validator module not available: {e}. Some endpoints will be disabled.")
    LEAD_VALIDATOR_AVAILABLE = False

lead_scheduler: Optional[AsyncIOScheduler] = None

app = FastAPI(
    title="Analytics SAAS API",
    description="Professional API for Advertising Campaign Analytics. Supports Yandex Direct, VK Ads, and Yandex Metrica.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Инициализация при старте приложения"""
    from automation.request_queue import get_request_queue
    await get_request_queue()  # Инициализируем очередь запросов
    logger.info("✅ Application startup complete - request queue initialized")

    # Админ-панель: сидинг дефолтных SEO-страниц (идемпотентно, best-effort).
    try:
        from core.config import get_config
        if get_config().internal_admin.enabled:
            from core.database import SessionLocal
            from internal_admin.bootstrap import ensure_default_seo_pages
            _db = SessionLocal()
            try:
                ensure_default_seo_pages(_db)
                logger.info("✅ Internal admin SEO pages seeded")
            finally:
                _db.close()
    except Exception as e:
        logger.warning("Internal admin bootstrap skipped: %s", e)

    # Воркер очереди синхронизации держим в backend и стартуем при загрузке —
    # он обрабатывает и ручные задачи, и ночные авто-задачи (их ставит automation).
    try:
        from backend_api.sync_jobs import ensure_sync_worker_started
        ensure_sync_worker_started()
        logger.info("✅ Sync job worker started")
    except Exception as e:
        logger.error(f"Failed to start sync job worker: {e}")

    # Планировщик для задач телефонии и отчётов
    global lead_scheduler
    lead_scheduler = AsyncIOScheduler()
    if LEAD_VALIDATOR_AVAILABLE:
        lead_scheduler.add_job(run_daily_alerts, "cron", hour=9, minute=0, id="lead_daily_alerts")
        lead_scheduler.add_job(run_weekly_report, "cron", day_of_week="mon", hour=9, minute=30, id="lead_weekly_report")
    if REPORTS_AVAILABLE:
        from backend_api.reports.scheduler import run_scheduled_report_rules
        # Финальная система: только одно проектное расписание. Legacy user.report_schedule
        # намеренно не запускается — иначе оно обходит очередь одобрения и дублирует отправки.
        lead_scheduler.add_job(run_scheduled_report_rules, "cron", minute="*", id="report_schedule_rules")
    # Pending personal VK links are not integrations yet: expire their public
    # capability promptly and remove abandoned drafts after the retention window.
    from backend_api.integrations import maintain_vk_client_links
    lead_scheduler.add_job(
        maintain_vk_client_links,
        "interval",
        hours=1,
        id="vk_client_link_maintenance",
        replace_existing=True,
    )
    # AI-комментарий к дашборду генерится ТОЛЬКО вручную (кнопка «Обновить» /
    # «Рассчитать») — по решению владельца от 2026-07-27: автогенерация (ночью
    # 56×3 вызова) слишком дорога на текущем AI-провайдере. Ночной джоб
    # намеренно НЕ планируется; функция generate_dashboard_comments оставлена
    # для ручного/будущего запуска.
    if lead_scheduler.get_jobs():
        lead_scheduler.start()
        logger.info("✅ Scheduler started (leads + reports)")

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения"""
    from automation.request_queue import shutdown_request_queue
    await shutdown_request_queue()
    logger.info("✅ Application shutdown complete - request queue stopped")

    global lead_scheduler
    if lead_scheduler:
        lead_scheduler.shutdown()
        lead_scheduler = None
        logger.info("✅ Lead validator scheduler stopped")


@app.middleware("http")
async def request_id_logging_middleware(request: Request, call_next):
    """
    Добавляет X-Request-ID к каждому запросу и логирует его.
    Если заголовок уже пришёл от прокси, переиспользуем его.
    """
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start_time = time.time()

    # Пробрасываем request_id дальше по пайплайну (если где-то пригодится)
    request.state.request_id = request_id

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"[{request_id}] {request.client.host if request.client else '-'} "
        f"{request.method} {request.url.path} -> {response.status_code} "
        f"({duration_ms:.1f} ms)"
    )

    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import json
    logger.error(f"Validation Error on {request.url.path}: {exc.errors()}")
    logger.error(f"Request body: {exc.body if hasattr(exc, 'body') else 'N/A'}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body) if hasattr(exc, 'body') else None},
    )

app.include_router(auth_router, prefix="/api")
app.include_router(oauth_login_router, prefix="/api")
app.include_router(telegram_link_router, prefix="/api")
app.include_router(telegram_webhook_router, prefix="/api")
app.include_router(max_reports_link_router, prefix="/api")
app.include_router(max_reports_webhook_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(folders_router, prefix="/api")
app.include_router(directions_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")
app.include_router(phone_projects_router, prefix="/api")
app.include_router(phone_leads_router, prefix="/api")
app.include_router(phone_stats_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(support_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(team_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(internal_admin_router, prefix="/api")
app.include_router(internal_manager_router, prefix="/api")
app.include_router(internal_seo_router, prefix="/api")
app.include_router(internal_auth_public_router, prefix="/api")
app.include_router(detector_router, prefix="/api")
app.include_router(brand_router, prefix="/api")

if AI_AVAILABLE:
    app.include_router(ai_router, prefix="/api")

if REPORTS_AVAILABLE:
    app.include_router(reports_router, prefix="/api")

# Lead Validator routers (публичные webhook'и и защищённые эндпоинты)
if LEAD_VALIDATOR_AVAILABLE:
    app.include_router(lead_validator_router, prefix="/api")
    app.include_router(webhook_router, prefix="/api")  # Публичные webhook'и для Tilda/Marquiz

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_uploads_dir = Path(os.getenv("UPLOADS_DIR", "uploads")).resolve()
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")
logger.info("Uploads static mounted at /uploads/ from %s", _uploads_dir)

# The admin SPA (Vue) is served by Nginx in the frontend container.
# Лендинг AdMirra: единственный источник — Vue `public/admirra`
# (Landing.vue: iframe src="/admirra/index.html"). Vite копирует public в dist.
# Ниже — та же папка на бэкенде для прямого доступа к :8001/admirra/


def _resolve_admirra_static_dir() -> Optional[Path]:
    """
    Только путь внутри trafic_agent:
    admin-panel-vue-main/admin-panel-vue-main/public/admirra
    """
    here = Path(__file__).resolve().parent
    trafic_agent_root = here.parent
    candidate = (
        trafic_agent_root
        / "admin-panel-vue-main"
        / "admin-panel-vue-main"
        / "public"
        / "admirra"
    )
    if candidate.is_dir() and (candidate / "index.html").is_file():
        return candidate
    return None


_admirra_dir = _resolve_admirra_static_dir()
if _admirra_dir is not None:
    app.mount(
        "/admirra",
        StaticFiles(directory=str(_admirra_dir), html=True),
        name="admirra",
    )
    logger.info("AdMirra static mounted at /admirra/ from %s", _admirra_dir)
else:
    logger.warning(
        "AdMirra static not found (expected admin-panel-vue-main/.../public/admirra)"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_api.main:app", host="0.0.0.0", port=8000, reload=True)
