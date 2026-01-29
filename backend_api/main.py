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

from backend_api.auth import router as auth_router
from backend_api.integrations import router as integrations_router
from backend_api.stats import router as stats_router
from backend_api.clients import router as clients_router
from backend_api.campaigns import router as campaigns_router
from backend_api.phone_projects import router as phone_projects_router

# Lead Validator routers (публичные webhook'и и защищённые эндпоинты)
try:
    from lead_validator.router import router as lead_validator_router
    from lead_validator.webhook_router import router as webhook_router
    LEAD_VALIDATOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Lead Validator module not available: {e}. Some endpoints will be disabled.")
    LEAD_VALIDATOR_AVAILABLE = False

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

@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения"""
    from automation.request_queue import shutdown_request_queue
    await shutdown_request_queue()
    logger.info("✅ Application shutdown complete - request queue stopped")


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
app.include_router(clients_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")
app.include_router(phone_projects_router, prefix="/api")

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

# The frontend is served by Nginx in the frontend container.
# The backend only needs to provide the API.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend_api.main:app", host="0.0.0.0", port=8000, reload=True)
