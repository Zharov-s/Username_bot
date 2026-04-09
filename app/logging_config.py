from __future__ import annotations

import logging
from logging.config import dictConfig


def setup_logging(level: str = "INFO") -> None:
    normalized = level.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": normalized,
                    "formatter": "standard",
                }
            },
            "root": {"handlers": ["console"], "level": normalized},
        }
    )
    logging.getLogger(__name__).info("Logging initialized with level=%s", normalized)
