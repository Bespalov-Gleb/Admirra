import logging
import time
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse # Changed from fastapi.responses.FileResponse
from core.database import engine
from core import models
import os

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

app = FastAPI(
    title="Analytics SAAS API",
    description="Professional API for Advertising Campaign Analytics. Supports Yandex Direct, VK Ads, and Yandex Metrica.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    import json
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

app.include_router(auth_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")

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
