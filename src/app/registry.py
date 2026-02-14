"""Generic registry for storing and retrieving objects by name."""

from collections.abc import Generator


class Registry[T]:
    """A simple registry to store and retrieve objects by name."""

    def __init__(self) -> None:
        self._registry: dict[str, T] = {}

    def register(self, name: str, obj: T) -> None:
        """Register an object with a given name."""
        self._registry[name] = obj

    def get(self, name: str) -> T | None:
        """Retrieve an object by its name."""
        return self._registry.get(name)

    def unregister(self, name: str) -> None:
        """Unregister an object by its name."""
        if name in self._registry:
            del self._registry[name]

    def clear(self) -> None:
        """Clear all registered objects."""
        self._registry.clear()

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Return all registered items as (name, object) pairs."""
        yield from self._registry.items()
