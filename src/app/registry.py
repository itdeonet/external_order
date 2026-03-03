"""Thread-safe generic registry for storing and retrieving objects by name.

This module provides a flexible Registry class that can store any type of object
and retrieve them by unique string names. All operations are thread-safe using locks,
making it suitable for multi-threaded environments. It's commonly used to manage
collections of service implementations (e.g., order services, artwork services).
"""

from collections.abc import Generator
from dataclasses import dataclass, field
from logging import getLogger
from threading import Lock

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Registry[T]:
    """Thread-safe generic registry for managing named object instances.

    A simple but powerful registry pattern implementation that allows registering,
    retrieving, and managing objects of any type (T) by unique string names.
    All operations are protected by locks to ensure thread safety.

    This is commonly used to manage collections of service implementations or
    factories, allowing the application to dynamically register and access them
    without tight coupling.

    Attributes:
        _registry: Internal dict storing name -> object mappings (thread-protected).
        _lock: Threading lock ensuring all operations are thread-safe.

    Example:
        >>> registry = Registry[OrderService]()
        >>> registry.register("harman", harman_service)
        >>> registry.register("spectrum", spectrum_service)
        >>> service = registry.get("harman")
        >>> for name, service in registry.items():
        ...     print(f"{name}: {service}")
    """

    _registry: dict[str, T] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def register(self, name: str, obj: T) -> None:
        """Register an object with a unique name in the registry.

        Thread-safe registration of an object. Names must be non-empty strings.
        If a name already exists, it is overwritten with the new object.

        Args:
            name: The unique identifier for the object. Must be a non-empty string.
            obj: The object to register.

        Raises:
            ValueError: If name is empty or not a string.
        """
        if not (isinstance(name, str) and name.strip()):
            raise ValueError("Name must be a non-empty string")
        with self._lock:
            self._registry[name] = obj

    def get(self, name: str) -> T | None:
        """Retrieve a registered object by its name.

        Thread-safe lookup of a registered object. Returns None if the name
        is not found in the registry.

        Args:
            name: The name of the object to retrieve.

        Returns:
            The registered object if found, None otherwise.
        """
        with self._lock:
            return self._registry.get(name)

    def unregister(self, name: str) -> None:
        """Unregister an object from the registry by its name.

        Thread-safe removal of a registered object. Logs a warning if attempting
        to unregister a name that is not registered.

        Args:
            name: The name of the object to unregister.
        """
        with self._lock:
            if name in self._registry:
                del self._registry[name]
            else:
                logger.warning("Attempted to unregister non-existent name: %s", name)

    def clear(self) -> None:
        """Remove all registered objects from the registry.

        Thread-safe operation that clears all entries, effectively resetting
        the registry to an empty state.
        """
        with self._lock:
            self._registry.clear()

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Iterate over all registered (name, object) pairs.

        Thread-safe iteration generator. Creates a snapshot of items at call time
        to avoid RuntimeError if the registry is modified during iteration.

        Yields:
            Tuples of (name, object) for each registered item.

        Example:
            >>> for service_name, service in registry.items():
            ...     print(f"Processing {service_name}...")
            ...     service.process()
        """
        with self._lock:
            # Create a snapshot to avoid RuntimeError during iteration
            items_snapshot = list(self._registry.items())
        yield from items_snapshot
