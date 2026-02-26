"""Use case interfaces."""

from typing import Protocol


class IUseCase(Protocol):
    """Interface for use cases."""

    def execute(self) -> None:
        """Execute the use case."""
        ...
