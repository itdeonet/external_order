"""Logging configuration and setup for the application.

This module provides utilities for configuring the logging system with both
console and file handlers. It sets up rotating file logs and controls log
levels for third-party libraries.
"""

import logging.config
from pathlib import Path


def configure_logging(log_file: Path, backup_count: int, log_file_level: str) -> None:
    """Configure and apply the global logging configuration.

    Sets up logging with console and file handlers. Console output is limited
    to WARNING and above, while file output captures all messages at the
    specified level. Includes timed rotation for log files and special
    configuration for httpx and httpcore loggers.

    Args:
        log_file: Path to the log file for file handler.
        backup_count: Number of backup log files to keep.
        log_file_level: Log level for file handler.
            Accepts standard Python log level strings (DEBUG, INFO, WARNING, etc.).
    """
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
