import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Path to the specific debug log file
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "integration_debug.log")
STRUCTURED_LOG_FILE = os.path.join(LOG_DIR, "structured.log")

# Ensure logs directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configure a specific logger for integration tracing
trace_logger = logging.getLogger("integration_trace")
trace_logger.setLevel(logging.INFO)

# Create file handler
fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
trace_logger.addHandler(fh)

# Structured logger for JSON logs
structured_logger = logging.getLogger("structured")
structured_logger.setLevel(logging.INFO)
sfh = logging.FileHandler(STRUCTURED_LOG_FILE, encoding='utf-8')
sfh.setFormatter(logging.Formatter('%(message)s'))  # Raw JSON
structured_logger.addHandler(sfh)

def log_event(source: str, message: str, data: any = None):
    """
    Logs an event to the integration debug log.
    source: frontend, backend, database, yandex, etc.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{source.upper()}] {message}"
    if data:
        log_msg += f" | Data: {data}"
    
    trace_logger.info(log_msg)
    # Also print to standard output for container visibility
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
