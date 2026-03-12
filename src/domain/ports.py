"""Interface protocols for dependency injection and services.

Defines Protocols used across the application (use cases, registries,
order/artwork/sale/stock service interfaces).
"""

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.domain import Order, OrderStatus


# ============================================================================
# Use Case Interface
# ============================================================================


class IUseCase(Protocol):
    """Protocol for a use case; implement `execute()` to run the workflow."""

    def execute(self) -> None:
        """Run the use case workflow; implementations handle errors as needed."""
        ...


# ============================================================================
# Registry Interface (Generic)
# ============================================================================


class IRegistry[T](Protocol):
    """Thread-safe registry Protocol for named service instances."""

    def register(self, name: str, obj: T) -> None:
        """Register or replace an object by name."""
        ...

    def get(self, name: str) -> T | None:
        """Return the object registered under `name`, or None."""
        ...

    def unregister(self, name: str) -> None:
        """Remove a named object from the registry (no-op if missing)."""
        ...

    def clear(self) -> None:
        """Remove all entries from the registry."""
        ...

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Yield (name, object) pairs for registered items."""
        ...


# ============================================================================
# Artwork Service Interface
# ============================================================================


class IArtworkService(Protocol):
    """Protocol to retrieve artwork files for an `Order`."""

    def get_artwork(self, order: "Order") -> list[Path]:
        """Return local `Path` list of artwork files for `order`."""
        ...


# ============================================================================
# Order Service Interfaces (Segregated)
# ============================================================================


class IOrderReader(Protocol):
    """Protocol to read orders from a provider; yields `Order` objects."""

    def read_orders(self) -> Generator["Order", None, None]:
        """Yield `Order` instances from the provider; may raise on errors."""
        ...


class IOrderStore(Protocol):
    """Protocol for persisting and loading `Order` objects."""

    def persist_order(self, order: "Order", status: "OrderStatus") -> None:
        """Persist `order` with `status`; may raise on storage errors."""
        ...

    def load_order(self, remote_order_id: str) -> "Order":
        """Return `Order` for `remote_order_id`; may raise if not found."""
        ...


class IOrderNotifier(Protocol):
    """Protocol to notify providers that an order's sale is complete."""

    def notify_completed_sale(self, order: "Order") -> None:
        """Send completion notification for `order` to its provider."""
        ...


class IArtworkServiceProvider(Protocol):
    """Select an `IArtworkService` from a registry for a given `Order`."""

    def get_artwork_service(
        self, order: "Order", artwork_services: "IRegistry[IArtworkService]"
    ) -> IArtworkService | None:
        """Return matching `IArtworkService` for `order`, or None."""
        ...


class IOrderService(IOrderReader, IOrderStore, IOrderNotifier, IArtworkServiceProvider, Protocol):
    """Composite Protocol aggregating order read/store/notify and artwork selection."""

    def should_update_sale(self, order: "Order") -> bool:
        """Determine if an existing sale should be updated based on `order` data."""
        ...


# ============================================================================
# Sale Service Interface
# ============================================================================


class ISaleService(Protocol):
    """Protocol for creating and managing sales for orders."""

    def create_sale(self, order: "Order") -> int:
        """Create a sale for `order` and return its ID; may raise on errors."""
        ...

    def confirm_sale(self, order: "Order") -> None:
        """Confirm the sale for `order` in the sales system."""
        ...

    def sale_has_expected_order_lines(self, order: "Order") -> bool:
        """Return True if sale lines match `order` lines, else False."""
        ...

    def update_contact(self, order: "Order") -> None:
        """Update sale contact details to match `order`."""
        ...

    def update_sale(self, order: "Order") -> None:
        """Update sale from `order`."""
        ...

    def search_sale(self, order: "Order") -> dict[str, Any]:
        """Return sale data for `order` if exists, else empty dict."""
        ...

    def search_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Return list of completed sales as (sale_id, remote_order_id) tuples."""
        ...

    def search_shipping_info(self, order: "Order") -> list[dict[str, Any]]:
        """Return shipping info for `order` as a list of dicts."""
        ...

    def search_serials_by_line_item(self, order: "Order") -> dict[str, list[str]]:
        """Return serial numbers per line item for `order`."""
        ...


# ============================================================================
# Stock Service Interface
# ============================================================================


class IStockService(Protocol):
    """Protocol for reading and replying to stock transfer notifications."""

    def read_stock_transfers(self) -> Generator[dict[str, Any], None, None]:
        """Yield stock transfer dicts; may raise on errors."""
        ...

    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Acknowledge `transfer_data` to supplier; may raise on errors."""
        ...
