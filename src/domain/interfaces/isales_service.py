"""Sale service interface."""

from pathlib import Path
from typing import Any, Protocol

from src.domain.order import Order


class ISalesService(Protocol):
    """Interface for sale services."""

    def create_sale(self, order: Order) -> int:
        """Create a sale for the given order."""
        ...

    def confirm_sale(self, sale_id: int) -> None:
        """Confirm the sale with the given ID."""
        ...

    def get_sale(self, order: Order) -> dict[str, Any]:
        """Get the sale order for the given order, if it exists."""
        ...

    def update_contact(self, order: Order) -> bool:
        """Update contact for an order in the sales system."""
        ...

    def verify_sale_quantities(self, order: Order, sale: dict[str, Any]) -> bool:
        """Verify sale order line quantities for an order in the sales system."""
        ...

    def prepare_artwork(self, order: Order, files: list[Path]) -> None:
        """Prepare artwork for the given order."""
        ...

    def get_completed_sales(self, order_provider: str) -> list[int]:
        """Get a list of completed sales."""
        ...
