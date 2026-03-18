"""Thread-safe registry for storing and retrieving objects by name.

Provides a simple `Registry[T]` to register, get, unregister, clear, and iterate
named objects in a thread-safe manner.
"""

from collections.abc import Generator
from dataclasses import dataclass, field
from functools import cache
from logging import getLogger
from threading import Lock

from src.domain import (
    IArtworkService,
    IOrderService,
    IRegistry,
    ISaleService,
    IStockService,
    IUseCase,
)

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Registry[T]:
    """Thread-safe generic registry for named object instances.

    Use to register and retrieve objects by string name; operations use a lock
    to ensure thread safety.
    """

    _registry: dict[str, T] = field(default_factory=dict, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def register(self, name: str, obj: T) -> None:
        """Register or overwrite `obj` under `name`.

        Raises `ValueError` for empty or non-string `name`.
        """
        if not (isinstance(name, str) and name.strip()):
            raise ValueError("Name must be a non-empty string")
        with self._lock:
            self._registry[name] = obj

    def get(self, name: str) -> T | None:
        """Return the object registered under `name`, or `None` if missing."""
        with self._lock:
            return self._registry.get(name)

    def unregister(self, name: str) -> None:
        """Remove the object registered under `name`; logs if it doesn't exist."""
        with self._lock:
            if name in self._registry:
                del self._registry[name]
            else:
                logger.warning("Attempted to unregister non-existent name: %s", name)

    def clear(self) -> None:
        """Clear all registered entries."""
        with self._lock:
            self._registry.clear()

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Yield a snapshot of (name, object) pairs for safe iteration."""
        with self._lock:
            # Create a snapshot to avoid RuntimeError during iteration
            items_snapshot = list(self._registry.items())
        yield from items_snapshot


@cache
def get_artwork_services() -> IRegistry[IArtworkService]:
    return Registry[IArtworkService]()


@cache
def get_order_services() -> IRegistry[IOrderService]:
    return Registry[IOrderService]()


@cache
def get_sale_services() -> IRegistry[ISaleService]:
    return Registry[ISaleService]()


@cache
def get_stock_services() -> IRegistry[IStockService]:
    return Registry[IStockService]()


@cache
def get_use_cases() -> IRegistry[IUseCase]:
    return Registry[IUseCase]()
