"""Generic registry for storing and retrieving objects by name."""

from collections.abc import Generator
from dataclasses import dataclass, field
from logging import getLogger
from threading import Lock

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Registry[T]:
    """A simple registry to store and retrieve objects by name."""

    _registry: dict[str, T] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def register(self, name: str, obj: T) -> None:
        """Register an object with a given name."""
        if not (isinstance(name, str) and name.strip()):
            raise ValueError("Name must be a non-empty string")
        with self._lock:
            self._registry[name] = obj

    def get(self, name: str) -> T | None:
        """Retrieve an object by its name."""
        with self._lock:
            return self._registry.get(name)

    def unregister(self, name: str) -> None:
        """Unregister an object by its name."""
        with self._lock:
            if name in self._registry:
                del self._registry[name]
            else:
                logger.warning("Attempted to unregister non-existent name: %s", name)

    def clear(self) -> None:
        """Clear all registered objects."""
        with self._lock:
            self._registry.clear()

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Return all registered items as (name, object) pairs."""
        with self._lock:
            # Create a snapshot to avoid RuntimeError during iteration
            items_snapshot = list(self._registry.items())
        yield from items_snapshot
