"""Errors module."""

import queue
from traceback import TracebackException


class ErrorQueue:
    """A thread-safe queue to store exceptions."""

    def __init__(self) -> None:
        self._queue: queue.Queue[TracebackException] = queue.Queue()

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


class InsdesError(Exception):
    """Custom exception for INSDES processing errors."""

    def __init__(self, message: str, order_id: str | None = None) -> None:
        super().__init__(message)
        self.order_id = order_id

    def __str__(self) -> str:
        base_message = super().__str__()
        if self.order_id:
            return f"{base_message} (Order ID: {self.order_id})"
        return base_message


class SaleError(Exception):
    """Raised for sale related errors."""

    def __init__(self, message: str, order_id: str | None = None) -> None:
        super().__init__(message)
        self.order_id = order_id

    def __str__(self) -> str:
        base_message = super().__str__()
        if self.order_id:
            return f"{base_message} (Order ID: {self.order_id})"
        return base_message
