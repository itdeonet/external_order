"""Core interface protocols for the application."""

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.domain import Order, OrderStatus


# ============================================================================
# Use Case Interface
# ============================================================================


class IUseCase(Protocol):
    """Interface for use cases."""

    def execute(self) -> None:
        """Execute the use case."""
        ...


# ============================================================================
# Registry Interface (Generic)
# ============================================================================


class IRegistry[T](Protocol):
    """A simple registry to store and retrieve objects by name."""

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


# ============================================================================
# Error Queue Interface
# ============================================================================


class IErrorQueue(Protocol):
    """Interface for a thread-safe queue to store exceptions."""

    def put(self, exc: Exception) -> None:
        """Add an exception to the queue."""
        ...

    def clear(self) -> None:
        """Clear all exceptions from the queue."""
        ...

    def summarize(self) -> str:
        """Summarize all collected exceptions."""
        ...


# ============================================================================
# Artwork Service Interface
# ============================================================================


class IArtworkService(Protocol):
    """Interface for artwork services."""

    def get_artwork(self, order: "Order") -> list[Path]:
        """Get artwork data for the given order."""
        ...


# ============================================================================
# Order Service Interfaces (Segregated)
# ============================================================================


class IOrderReader(Protocol):
    """Interface for reading orders from a provider."""

    def read_orders(self, error_queue: IErrorQueue) -> Generator["Order", None, None]:
        """Generate orders from the provider."""
        ...


class IOrderStore(Protocol):
    """Interface for storing and retrieving orders."""

    def persist_order(self, order: "Order", status: "OrderStatus") -> None:
        """Save the given order with its current status."""
        ...

    def load_order(self, remote_order_id: str) -> "Order | None":
        """Load an order by its remote ID, or None if not found."""
        ...


class IOrderNotifier(Protocol):
    """Interface for notifying the order provider of order events."""

    def notify_completed_sale(self, order: "Order") -> None:
        """Notify the order provider that a sale order has been completed."""
        ...


class IArtworkServiceProvider(Protocol):
    """Interface for providing artwork services based on order."""

    def get_artwork_service(
        self, order: "Order", artwork_services: "IRegistry[IArtworkService]"
    ) -> IArtworkService | None:
        """Get the appropriate artwork service for the given order, or None if not found."""
        ...


class IOrderService(IOrderReader, IOrderStore, IOrderNotifier, IArtworkServiceProvider, Protocol):
    """Composite interface for full-featured order services.

    Combines all order-related operations: reading, storing, notifying, and artwork provisioning.
    Use specific interfaces (IOrderReader, IOrderStore, etc.) when only certain operations are needed.
    """

    ...


# ============================================================================
# Sale Service Interface
# ============================================================================


class ISaleService(Protocol):
    """Interface for sales services."""

    def is_sale_created(self, order: "Order") -> bool:
        """Check if a sale has already been created for the given order."""
        ...

    def create_sale(self, order: "Order") -> int:
        """Create a sale for the given order and return its ID."""
        ...

    def confirm_sale(self, order: "Order") -> None:
        """Confirm the sale for the given order."""
        ...

    def has_expected_order_lines(self, order: "Order") -> bool:
        """Verify that the sale has the same order line quantities as the local order."""
        ...

    def update_contact(self, order: "Order") -> None:
        """Update the contact information for the given order."""
        ...

    def get_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Get a list of completed sales."""
        ...

    def get_shipping_info(self, order: "Order") -> list[dict[str, Any]]:
        """Get the shipping information for the given order."""
        ...

    def get_serials_by_line_item(self, order: "Order") -> dict[str, list[str]]:
        """Get the serial numbers for the given order by line item."""
        ...


# ============================================================================
# Stock Service Interface
# ============================================================================


class IStockService(Protocol):
    """Interface for stock transfer services."""

    def read_stock_transfers(
        self, error_queue: IErrorQueue
    ) -> Generator[dict[str, Any], None, None]:
        """Read stock transfer requests."""
        ...

    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Reply to stock transfer requests."""
        ...
