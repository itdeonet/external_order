"""LineItem domain model.

Represents a product line in an order. Validates fields and optional artwork.
"""

from dataclasses import dataclass

import src.domain.validators as validators
from src.domain.artwork import Artwork


@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    """Immutable line item model.

    Holds product code, quantity, and optional `Artwork`. Validates inputs.
    """

    line_id: str
    product_code: str
    quantity: int
    artwork: Artwork | None = None

    def __post_init__(self) -> None:
        """Validate and normalize fields; raise ValueError on invalid input."""
        validators.validate_non_empty_string(self.line_id, "Line ID")
        validators.set_normalized_string(self, "line_id", self.line_id)

        validators.validate_non_empty_string(self.product_code, "Product code")
        validators.set_normalized_string(self, "product_code", self.product_code)

        validators.validate_positive_int(self.quantity, "Quantity")

        # artwork is optional, but if provided must be an Artwork instance
        if self.artwork is not None and not isinstance(self.artwork, Artwork):
            raise ValueError("Artwork must be an instance of Artwork or None")

    def set_artwork(self, artwork: Artwork) -> None:
        """Set artwork for this line item; requires an `Artwork` instance."""
        if not isinstance(artwork, Artwork):
            raise ValueError("Artwork must be an instance of Artwork")
        object.__setattr__(self, "artwork", artwork)
