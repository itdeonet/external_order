"""Error handling utilities and custom exceptions.

Provides a thread-safe `ErrorStore` and domain-specific exceptions.
"""

import datetime as dt
from dataclasses import dataclass, field
from functools import cache
from threading import Lock
from traceback import TracebackException
from typing import Any

from src.config import get_config


@dataclass(frozen=True, slots=True)
class ErrorStore:
    """Thread-safe collector for application exceptions.

    Use `get_error_store()` to obtain the shared instance.
    """

    _errors: list[Exception] = field(default_factory=list, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def add(self, exc: Exception) -> None:
        """Store `exc` (with traceback) in the error list."""
        with self._lock:
            self._errors.append(exc)

    def clear(self) -> None:
        """Remove all stored errors."""
        with self._lock:
            self._errors.clear()

    def all(self) -> list[str]:
        """Return formatted tracebacks for all stored exceptions."""
        with self._lock:
            if not self._errors:
                return []
            errors = []
            for idx, error in enumerate(self._errors, 1):
                traceback = TracebackException.from_exception(error)
                errors.append(f"Error {idx}:\n{error}\n{''.join(traceback.format())}")
            return errors

    def get_render_email_data(self) -> dict[str, Any]:
        """Return a dict with error count, formatted errors, timestamp, and company."""
        return {
            "error_count": len(self._errors),
            "errors": self.all(),
            "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "company_name": get_config().sale_company_name,
        }

    def has_errors(self) -> bool:
        """Return True if any errors are stored."""
        with self._lock:
            return bool(self._errors)

    def summarize(self) -> str:
        """Return all errors as a single multi-line string."""
        return "\n\n".join(self.all())


@cache
def get_error_store() -> ErrorStore:
    """Return the cached singleton `ErrorStore` instance."""
    return ErrorStore()


class BaseError(Exception):
    """Base exception that holds an optional `order_id` context."""

    def __init__(self, message: str, order_id: str | None = None) -> None:
        super().__init__(message)
        self.order_id = order_id

    def __str__(self) -> str:
        if self.order_id:
            return f"Order {self.order_id}: {super().__str__()}"
        return super().__str__()


class ArtworkError(BaseError):
    """Raised for artwork retrieval/processing failures."""

    pass


class InsdesError(BaseError):
    """Raised for .insdes file processing errors."""

    pass


class OrderError(BaseError):
    """Raised for order-related failures (load/validation)."""

    pass


class NotifyError(BaseError):
    """Raised when notifying an order provider fails."""

    pass


class SaleError(BaseError):
    """Raised for sale-related failures (create/update/confirm)."""

    pass
