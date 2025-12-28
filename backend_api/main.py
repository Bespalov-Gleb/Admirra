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

# Enable automatic table creation
models.Base.metadata.create_all(bind=engine)

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

app = FastAPI(
    title="Analytics SAAS API",
    description="Professional API for Advertising Campaign Analytics. Supports Yandex Direct, VK Ads, and Yandex Metrica.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(auth_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(stats_router, prefix="/api")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route for legacy pages - (Removed, handled by SPA)
# @app.get("/login") ...
# @app.get("/register") ...

# Mount assets and other static files
app.mount("/assets", StaticFiles(directory="public_html (17)/public_html/assets"), name="assets")

# Catch-all for Frontend (serves new layout from public_html (17))
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Don't intercept API calls
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})

    # Primary: check public_html (17)/public_html
    file_path = os.path.join("public_html (17)/public_html", full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Secondary: check frontend (fallback for specific pages like dashboard.html)
    old_file_path = os.path.join("frontend", full_path)
    if os.path.isfile(old_file_path):
        return FileResponse(old_file_path)

    # If path is empty or unknown, serve the main index.html from new layout
    return FileResponse("public_html (17)/public_html/index.html")
