"""Configure application logging (console + rotating file handlers)."""

import logging.config
from pathlib import Path


def configure_logging(log_file: Path, backup_count: int, log_file_level: str) -> None:
    """Apply logging config: console (WARNING+) and rotating file (given level)."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                },
                "console": {
                    "format": "%(levelname)s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "console",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": log_file_level,
                    "formatter": "standard",
                    "filename": str(log_file),
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "httpx": {"level": "INFO", "handlers": ["console"], "propagate": False},
                "httpcore": {"level": "INFO", "handlers": ["console"], "propagate": False},
            },
            "root": {
                "level": log_file_level,
                "handlers": ["console", "file"],
            },
        }
    )
