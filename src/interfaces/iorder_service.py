"""Order service interface."""

from collections.abc import Generator
from typing import Any, Protocol

from src.domain.order import Order, OrderStatus
from src.interfaces.iartwork_service import IArtworkService
from src.interfaces.ierror_queue import IErrorQueue
from src.interfaces.iregistry import IRegistry


class IOrderService(Protocol):
    """Interface for order services."""

    def get_orders(self, error_queue: IErrorQueue) -> Generator[Order, None, None]:
        """Generate orders."""
        ...

    def get_order_data_by_remote_order_id(self, remote_order_id: str) -> dict[str, Any] | None:
        """Get order data by remote ID."""
        ...

    def notify_completed_sale(self, order: Order) -> None:
        """Notify the order provider of a completed sale."""
        ...

    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Get the artwork service for the given order."""
        ...

    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Save the given order."""
        ...

    def load_order(self, remote_order_id: str) -> Order | None:
        """Load an order by remote ID."""
        ...
