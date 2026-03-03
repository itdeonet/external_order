"""Error management and custom exception types.

This module provides:
- ErrorStore: A thread-safe singleton for collecting and managing exceptions across the application
- Custom exception hierarchy: Domain-specific error types for different error scenarios

The ErrorStore is used throughout use cases to collect exceptions without stopping execution.
Custom exceptions allow callers to handle different error types appropriately.
"""

import datetime as dt
from dataclasses import dataclass, field
from threading import Lock
from traceback import TracebackException
from typing import Any, ClassVar, Self


@dataclass(frozen=True, slots=True)
class ErrorStore:
    """Thread-safe singleton for collecting and managing application exceptions.

    This class implements the singleton pattern to ensure a single instance is used
    throughout the application. All operations are thread-safe via locks.

    The ErrorStore collects exceptions from all use cases and makes them available
    for review, logging, and error reporting without interrupting normal execution.

    Usage:
        error_store = ErrorStore()  # Always returns the same instance
        error_store.add(some_exception)
        error_store.has_errors()  # Check if errors were collected
        error_store.summarize()  # Get formatted error summary
    """

    _instance: ClassVar[Self | None] = None
    _errors: list[TracebackException] = field(default_factory=list, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def __new__(cls) -> Self:
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def add(self, exc: Exception) -> None:
        """Add an exception to the thread-safe error collection.

        The exception is stored with its full traceback information for later inspection.
        This method is safe to call from multiple threads simultaneously.

        Args:
            exc: The exception to store.
        """
        with self._lock:
            self._errors.append(TracebackException.from_exception(exc))

    def clear(self) -> None:
        """Clear all exceptions from the store."""
        with self._lock:
            self._errors.clear()

    def all(self) -> list[str]:
        """Get all collected exceptions formatted with their full tracebacks.

        Returns:
            A list of formatted exception strings, one per error. Each includes
            the error number, type, message, and full stack trace. Empty list if
            no exceptions have been collected.
        """
        with self._lock:
            if not self._errors:
                return []
            errors = []
            for idx, error in enumerate(self._errors, 1):
                errors.append(f"Error {idx}:\n{''.join(error.format())}")
            return errors

    def get_render_email_data(self) -> dict[str, Any]:
        """Get formatted error data for rendering error notification email.

        Returns:
            A dictionary with keys:
            - 'error_count': Number of errors collected
            - 'errors': List of formatted error strings
            - 'timestamp': Current timestamp when method was called
        """
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
        """Get all collected exceptions as a single formatted string.

        Each exception is separated by a blank line and includes full traceback.

        Returns:
            A multi-line string with all errors formatted and separated.
            Empty string if no exceptions have been collected.
        """
        return "\n\n".join(self.all())


class BaseError(Exception):
    """Base exception for domain-specific error types.

    All custom exceptions in this module inherit from BaseError, providing
    a consistent way to capture context about which order is affected by an error.

    Attributes:
        message: The error message explaining what went wrong.
        order_id: Optional identifier of the affected order, simplifies error tracking.
    """

    def __init__(self, message: str, order_id: str | None = None) -> None:
        super().__init__(message)
        self.order_id = order_id

    def __str__(self) -> str:
        if self.order_id:
            return f"Order {self.order_id}: {super().__str__()}"
        return super().__str__()


class ArtworkError(BaseError):
    """Raised when artwork retrieval or processing fails.

    This includes errors from the artwork service, file download failures,
    invalid file formats, or missing artwork for orders.
    """

    pass


class InsdesError(BaseError):
    """Raised when .insdes file processing fails.

    This includes errors from parsing, validating, or processing .insdes files
    that are part of order information.
    """

    pass


class NotifyError(BaseError):
    """Raised when notification to an order provider fails.

    This includes failures to communicate status updates, completion notifications,
    or any other provider-specific notifications.
    """

    pass


class SaleError(BaseError):
    """Raised when sale operations fail.

    This includes errors from the Odoo sale service, order not found errors,
    validation failures, or any issue preventing sales from being created,
    updated, or completed.
    """

    pass
