"""Sale service interface."""

from typing import Any, Protocol

from src.domain.order import Order


class ISaleService(Protocol):
    """Interface for sales services."""

    def is_sale_created(self, order: Order) -> bool:
        """Check if a sale has already been created for the given order."""
        ...

    def create_sale(self, order: Order) -> int:
        """Create a sale for the given order and return its ID."""
        ...

    def confirm_sale(self, order: Order) -> None:
        """Confirm the sale for the given order."""
        ...

    def has_expected_order_lines(self, order: Order) -> bool:
        """Verify that the sale has the same order line quantities as the local order."""
        ...

    def update_contact(self, order: Order) -> None:
        """Update the contact information for the given order."""
        ...

    def get_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Get a list of completed sales."""
        ...

    def get_shipping_info(self, order: Order) -> list[dict[str, Any]]:
        """Get the shipping information for the given order."""
        ...

    def get_serials_by_line_item(self, order: Order) -> dict[str, list[str]]:
        """Get the serial numbers for the given order by line item."""
        ...
