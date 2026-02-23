"""Generic registry for storing and retrieving objects by name."""

from collections.abc import Generator
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Registry[T]:
    """A simple registry to store and retrieve objects by name."""

    registry: dict[str, T] = field(default_factory=dict, init=False, repr=False)

    def register(self, name: str, obj: T) -> None:
        """Register an object with a given name."""
        self.registry[name] = obj

    def get(self, name: str) -> T | None:
        """Retrieve an object by its name."""
        return self.registry.get(name)

    def unregister(self, name: str) -> None:
        """Unregister an object by its name."""
        if name in self.registry:
            del self.registry[name]

    def clear(self) -> None:
        """Clear all registered objects."""
        self.registry.clear()

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Return all registered items as (name, object) pairs."""
        yield from self.registry.items()
