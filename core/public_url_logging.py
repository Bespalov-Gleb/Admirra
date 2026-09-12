"""Redact report bearer capabilities without changing the actual request URL."""
import logging
import re

_PUBLIC_PATH = re.compile(r"(/(?:api/)?reports/(?:view/|file/|deliveries/public/))[^\s/?#\"']+")
_VERSIONED_TOKEN = re.compile(r"(?:r1|f1)_[A-Za-z0-9_-]{43}")


def redact(value):
    if isinstance(value, str):
        return _VERSIONED_TOKEN.sub("[report-token]", _PUBLIC_PATH.sub(r"\1[redacted]", value))
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value


class PublicURLFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact(record.msg)
        record.args = redact(record.args)
        return True


def install():
    # Uvicorn access has a dedicated non-propagating handler. Preserve argument
    # types for its AccessFormatter (status stays int; request_line stays str).
    for name in ("api", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        if not any(isinstance(item, PublicURLFilter) for item in logger.filters):
            logger.addFilter(PublicURLFilter())
