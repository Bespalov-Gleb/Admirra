"""
Настройки приложения (AI, отчёты и т.д.).
Переменные окружения загружаются через dotenv.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# OpenAI / AI Report
OPENAI_API_KEY: str = _get_env("OPENAI_API_KEY", "")
AI_PROXY_URL: str = _get_env("AI_PROXY_URL", "")  # e.g. "http://user:pass@proxy:8080"
OPENAI_MODEL: str = _get_env("OPENAI_MODEL", "gpt-4o-mini")
