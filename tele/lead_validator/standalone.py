"""
Standalone сервер для Lead Validator.
Не требует PostgreSQL, работает независимо от основного backend_api.

Запуск:
    python -m uvicorn lead_validator.standalone:app --reload --port 8000
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("lead_validator")

# Create standalone FastAPI app
app = FastAPI(
    title="Lead Validator API",
    description="Микросервис для валидации и фильтрации входящих лидов",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from lead_validator.router import router as lead_router
from lead_validator.webhook_router import router as webhook_router

app.include_router(lead_router, prefix="/api")


# Stub auth for demo
from lead_validator.auth_stub import router as auth_stub_router
app.include_router(auth_stub_router, prefix="/api")
app.include_router(webhook_router)  # /webhook/tilda/, /webhook/marquiz/

# === Static Files & SPA Serving ===
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib
import os

# Путь к папке dist (относительно standalone.py)
# trafic_agent/lead_validator/standalone.py -> trafic_agent/frontend/admin-panel-vue-main/dist
current_dir = pathlib.Path(__file__).parent.resolve()
dist_dir = current_dir.parent / "frontend" / "admin-panel-vue-main" / "dist"

if os.path.exists(dist_dir):
    logger.info(f"Serving frontend from: {dist_dir}")
    
    # Монтируем assets (CSS, JS, Images)
    app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")
    
    # Catch-all для SPA (Vue Router)
    # Этот роут должен быть ПОСЛЕДНИМ
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Если файл существует в dist (например, favicon.ico), отдаем его
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
            
        # Иначе отдаем index.html для роутинга на клиенте
        return FileResponse(str(dist_dir / "index.html"))
else:
    logger.warning(f"Frontend dist directory NOT FOUND at: {dist_dir}")
    logger.warning("Please runs 'npm run build' in frontend directory")


if __name__ == "__main__":
    import uvicorn
    # В продакшене лучше отключить reload
    uvicorn.run("lead_validator.standalone:app", host="0.0.0.0", port=8000, reload=False)
