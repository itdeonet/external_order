"""Errors module."""

import datetime as dt
from dataclasses import dataclass, field
from threading import Lock
from traceback import TracebackException
from typing import Any, ClassVar, Self


@dataclass(frozen=True, slots=True)
class ErrorStore:
    """A thread-safe store to store exceptions."""

    _instance: ClassVar[Self | None] = None
    _errors: list[TracebackException] = field(default_factory=list, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __new__(cls) -> Self:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def add(self, exc: Exception) -> None:
        """Add an exception to the store."""
        with self._lock:
            self._errors.append(TracebackException.from_exception(exc))

    def clear(self) -> None:
        """Clear all exceptions from the store."""
        with self._lock:
            self._errors.clear()

    def all(self) -> list[str]:
        """Summarize all collected exceptions."""
        with self._lock:
            if not self._errors:
                return []
            errors = []
            for idx, error in enumerate(self._errors, 1):
                errors.append(f"Error {idx}:\n{''.join(error.format())}")
            return errors

    def get_render_email_data(self) -> dict[str, Any]:
        """Get data for rendering error alert email."""
        return {
            "error_count": len(self._errors),
            "errors": self.all(),
            "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def has_errors(self) -> bool:
        """Check if there are any errors in the store."""
        with self._lock:
            return bool(self._errors)

    def summarize(self) -> str:
        """Get a summary of all collected exceptions as a single string."""
        return "\n\n".join(self.all())


class BaseError(Exception):
    """Base exception for custom errors."""

    def __init__(self, message: str, order_id: str | None = None) -> None:
        super().__init__(message)
        self.order_id = order_id

    def __str__(self) -> str:
        base_message = super().__str__()
        if self.order_id:
            return f"{base_message} (Order ID: {self.order_id})"
        return base_message


class ArtworkError(BaseError):
    """Raised for errors related to artwork retrieval."""

    pass


class InsdesError(BaseError):
    """Raised for errors related to .insdes file processing."""

    pass


class NotifyError(BaseError):
    """Raised for errors related to notifying order providers."""

    pass


class SaleError(BaseError):
    """Raised for sale related errors."""

    pass
