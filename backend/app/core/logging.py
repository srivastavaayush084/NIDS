import logging
import sys
from backend.app.core.config import settings


def setup_logging():
    """Configure structured logging for the backend application."""
    log_format = "%(asctime)s - [%(levelname)s] - [%(name)s] - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure root/app logger
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    app_logger = logging.getLogger("zero_day_detection")
    app_logger.setLevel(log_level)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not app_logger.handlers:
        app_logger.addHandler(handler)
        app_logger.propagate = False

    app_logger.info(f"Structured logging initialized at level {settings.LOG_LEVEL.upper()} (Environment: {settings.ENVIRONMENT})")
    return app_logger


logger = setup_logging()
