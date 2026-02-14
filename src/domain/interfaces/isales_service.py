"""Sale service interface."""

from pathlib import Path
from typing import Protocol

from src.domain.order import Order


class ISalesService(Protocol):
    """Interface for sale services."""

    def create_sale(self, order: Order) -> int:
        """Create a sale for the given order."""
        ...

    def prepare_artwork(self, order: Order, files: list[Path]) -> None:
        """Prepare artwork for the given order."""
        ...

    def get_completed_sales(self) -> list[int]:
        """Get a list of completed sales."""
        ...
