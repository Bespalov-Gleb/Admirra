import logging
import os
from datetime import datetime

# Path to the specific debug log file
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "integration_debug.log")

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
