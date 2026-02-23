"""Error queue interface."""

from traceback import TracebackException
from typing import Protocol


class IErrorQueue(Protocol):
    """Interface for a thread-safe queue to store exceptions."""

    def put(self, exc: Exception) -> None:
        """Add an exception to the queue."""
        ...

    def all(self) -> list[TracebackException]:
        """Retrieve all exceptions from the queue."""
        ...

    def clear(self) -> None:
        """Clear all exceptions from the queue."""
        ...

    def summarize(self) -> str:
        """Summarize all collected exceptions."""
        ...
