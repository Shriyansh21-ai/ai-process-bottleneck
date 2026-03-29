import logging
import sys
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
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
