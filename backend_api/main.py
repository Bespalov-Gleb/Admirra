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
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS platform_status VARCHAR"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS platform_state VARCHAR"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS display_status VARCHAR"))
                conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS status_synced_at TIMESTAMP WITH TIME ZONE"))
                conn.execute(text("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS utm_source VARCHAR"))
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
from backend_api.admin import router as admin_router
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
        from backend_api.reports.scheduler import run_scheduled_reports
        lead_scheduler.add_job(run_scheduled_reports, "cron", minute="*", id="report_scheduled_send")
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
app.include_router(admin_router, prefix="/api")
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
