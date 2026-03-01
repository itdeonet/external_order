"""Errors module."""

import datetime as dt
from dataclasses import dataclass, field
from threading import Lock
from traceback import TracebackException
from typing import Any


@dataclass(frozen=True, slots=True)
class ErrorQueue:
    """A thread-safe queue to store exceptions."""

    _errors: list[TracebackException] = field(default_factory=list, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def put(self, exc: Exception) -> None:
        """Add an exception to the queue."""
        with self._lock:
            self._errors.append(TracebackException.from_exception(exc))

    def clear(self) -> None:
        """Clear all exceptions from the queue."""
        with self._lock:
            self._errors.clear()

    def get_errors(self) -> list[str]:
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
            "errors": self.get_errors(),
            "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def summarize(self) -> str:
        """Get a summary of all collected exceptions as a single string."""
        return "\n\n".join(self.get_errors())


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
