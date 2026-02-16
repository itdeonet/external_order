"""Registry interface for storing and retrieving objects by name."""

from collections.abc import Generator
from typing import Protocol


class IRegistry[T](Protocol):
    """A simple registry to store and retrieve objects by name."""

    registry: dict[str, T]

    def register(self, name: str, obj: T) -> None:
        """Register an object with a given name."""
        ...

    def get(self, name: str) -> T | None:
        """Retrieve an object by its name."""
        ...

    def unregister(self, name: str) -> None:
        """Unregister an object by its name."""
        ...

    def clear(self) -> None:
        """Clear all registered objects."""
        ...

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Return all registered items as (name, object) pairs."""
        ...
