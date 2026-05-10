import logging
import sys
from logging.config import dictConfig


class RequestIDFormatter(logging.Formatter):
    """Custom formatter that provides a default value for request_id if missing."""
    
    def format(self, record):
        # Add request_id if it doesn't exist
        if not hasattr(record, 'request_id'):
            record.request_id = 'N/A'
        return super().format(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "src.core.logging.RequestIDFormatter",
            "format": (
                "%(asctime)s | %(levelname)s | "
                "request_id=%(request_id)s | "
                "%(name)s | %(message)s"
            )
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

def setup_logging():
    dictConfig(LOGGING_CONFIG)
