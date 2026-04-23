"""
Настройки приложения (AI, отчёты и т.д.).
Совместимый слой поверх core.config.get_config().
"""
from core.config import get_config

cfg = get_config()

# OpenAI / AI Report
OPENAI_API_KEY: str = cfg.openai.api_key
AI_PROXY_URL: str = ""  # e.g. "http://user:pass@proxy:8080"
OPENAI_MODEL: str = cfg.openai.model
