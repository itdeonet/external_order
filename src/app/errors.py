"""Errors module."""

import queue
from dataclasses import dataclass, field
from traceback import TracebackException


@dataclass(frozen=True, slots=True)
class ErrorQueue:
    """A thread-safe queue to store exceptions."""

    _queue: queue.Queue[TracebackException] = field(
        default_factory=queue.Queue, init=False, repr=False
    )

    def put(self, exc: Exception) -> None:
        """Add an exception to the queue."""
        self._queue.put(TracebackException.from_exception(exc))

    def all(self) -> list[TracebackException]:
        """Retrieve all exceptions from the queue."""
        errors = []
        while not self._queue.empty():
            errors.append(self._queue.get())
        return errors

    def clear(self) -> None:
        """Clear all exceptions from the queue."""
        while not self._queue.empty():
            self._queue.get()

    def summarize(self) -> str:
        """Summarize all collected exceptions."""
        errors = self.all()
        if not errors:
            return "No errors collected."
        summary = []
        for idx, error in enumerate(errors, 1):
            summary.append(f"Error {idx}:\n{''.join(error.format())}")
        return "\n\n".join(summary)


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
