import logging
import os
import json
from logging.handlers import RotatingFileHandler
from core.runtime import env_bool
from datetime import datetime
from typing import Optional, Dict, Any

# Path to the specific debug log file
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_TO_STDOUT = env_bool("LOG_TO_STDOUT", False)
LOG_FILE = os.path.join(LOG_DIR, "integration_debug.log")
STRUCTURED_LOG_FILE = os.path.join(LOG_DIR, "structured.log")

# Ensure logs directory exists
if not LOG_TO_STDOUT:
    os.makedirs(LOG_DIR, exist_ok=True)


def _handler(path):
    if LOG_TO_STDOUT:
        return logging.StreamHandler()
    return RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")

# Configure a specific logger for integration tracing
trace_logger = logging.getLogger("integration_trace")
trace_logger.setLevel(logging.INFO)

# Create file handler
fh = _handler(LOG_FILE)
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
trace_logger.addHandler(fh)
if LOG_TO_STDOUT:
    trace_logger.propagate = False

# Structured logger for JSON logs
structured_logger = logging.getLogger("structured")
structured_logger.setLevel(logging.INFO)
sfh = _handler(STRUCTURED_LOG_FILE)
sfh.setFormatter(logging.Formatter('%(message)s'))  # Raw JSON
structured_logger.addHandler(sfh)
if LOG_TO_STDOUT:
    structured_logger.propagate = False

def log_event(source: str, message: str, data: any = None, level: str = "info"):
    """
    Logs an event to the integration debug log.
    source: frontend, backend, database, yandex, etc.
    level: info | warning | error | debug (как у logging).
    """
    log_msg = f"[{source.upper()}] {message}"
    if data:
        log_msg += f" | Data: {data}"

    lvl = getattr(logging, str(level).upper(), logging.INFO)
    if not isinstance(lvl, int):
        lvl = logging.INFO
    trace_logger.log(lvl, log_msg)
    # Also print to standard output for container visibility
    if not LOG_TO_STDOUT:
        print(f"DEBUG_TRACE: {log_msg}")

def log_structured(
    level: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """
    Structured logging with JSON format and contextual information.
    
    Args:
        level: Log level (info, warning, error, debug)
        message: Log message
        context: Dictionary with contextual info (e.g., client_login, integration_id)
        **kwargs: Additional key-value pairs to include in log
        
    Example:
        log_structured('info', 'API call started', 
                      context={'client_login': 'user123', 'integration_id': 'abc-123'},
                      endpoint='get_campaigns', duration_ms=150)
    """
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level.upper(),
        'message': message,
    }
    
    if context:
        log_entry['context'] = context
    
    if kwargs:
        log_entry['extra'] = kwargs
    
    # Write JSON log
    structured_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    # Also log to trace for visibility
    if context:
        trace_logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"{message} | Context: {context} | Extra: {kwargs}"
        )
