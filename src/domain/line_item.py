"""A line item in an order."""

import uuid
from dataclasses import dataclass, field

import src.domain.validators as validators
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
        validators.validate_non_empty_string(self.remote_line_id, "Remote line ID")
        validators.set_normalized_string(self, "remote_line_id", self.remote_line_id)

        validators.validate_non_empty_string(self.product_code, "Product code")
        validators.set_normalized_string(self, "product_code", self.product_code)

        validators.validate_positive_int(self.quantity, "Quantity")

        # artwork is optional, but if provided must be an Artwork instance
        if self.artwork is not None and not isinstance(self.artwork, Artwork):
            raise ValueError("Artwork must be an instance of Artwork or None")

    def set_artwork(self, artwork: Artwork) -> None:
        """Set the artwork for the line item."""
        if not isinstance(artwork, Artwork):
            raise ValueError("Artwork must be an instance of Artwork")
        object.__setattr__(self, "artwork", artwork)
