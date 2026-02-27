"""A line item in an order."""

import uuid
from dataclasses import dataclass, field

from src.domain.artwork import Artwork


@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    """A line item in an order."""

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    remote_line_id: str
    product_code: str
    quantity: int
    artwork: Artwork | None = None

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if not (isinstance(self.remote_line_id, str) and self.remote_line_id.strip()):
            raise ValueError("Remote line ID must be a non-empty string")
        object.__setattr__(self, "remote_line_id", self.remote_line_id.strip())

        if not (isinstance(self.product_code, str) and self.product_code.strip()):
            raise ValueError("Product code must be a non-empty string")
        object.__setattr__(self, "product_code", self.product_code.strip())

        if not (isinstance(self.quantity, int) and self.quantity > 0):
            raise ValueError("Quantity must be a positive integer")

        if not (isinstance(self.artwork, Artwork) or self.artwork is None):
            raise ValueError("Artwork must be an instance of Artwork or None")

    def set_artwork(self, artwork: Artwork) -> None:
        """Set the artwork for the line item."""
        if not (artwork and (isinstance(artwork, Artwork))):
            raise ValueError("Artwork must be an instance of Artwork")
        object.__setattr__(self, "artwork", artwork)
