"""Order service interface."""

from collections.abc import Generator
from pathlib import Path
from typing import Protocol

from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.interfaces.ierror_queue import IErrorQueue
from src.domain.interfaces.iregistry import IRegistry
from src.domain.order import Order, OrderStatus


class IOrderService(Protocol):
    """Interface for order services."""

    @property
    def json_orders_dir(self) -> Path:
        """Get the JSON orders directory."""
        ...

    def get_orders(self, error_queue: IErrorQueue) -> Generator[Order, None, None]:
        """Generate orders."""
        ...

    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Get the artwork service for the given order."""
        ...

    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Save the given order."""
        ...
