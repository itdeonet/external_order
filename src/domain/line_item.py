"""Domain model for line items in an order.

This module defines the LineItem class, which represents a single line item
within an order. Each line item references a product and includes optional
additional artwork. Line items are immutable and validated at construction time.

Validation ensures:
- Remote line ID and product code are non-empty after normalization
- Quantity is a positive integer
- Artwork, if provided, is an Artwork instance
"""

import uuid
from dataclasses import dataclass, field

import src.domain.validators as validators
from src.domain.artwork import Artwork


@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    """Immutable line item model representing a product within an order.

    A line item specifies a product to be ordered with a quantity. It may
    optionally include artwork specifications. All fields are validated during
    post-initialization and are immutable after construction.

    This class enforces:
    - Immutability: All attributes are read-only after object creation
    - Validation: All fields must meet strict requirements
    - String normalization: IDs are trimmed and normalized
    - Artwork integrity: Only Artwork instances are accepted

    Attributes:
        id: Unique auto-generated UUID for this line item
        remote_line_id: External identifier from the order source system
        product_code: Code or SKU identifying the product to order
        quantity: Number of units to order (must be positive)
        artwork: Optional Artwork instance for design specifications

    Example:
        >>> line_item = LineItem(remote_line_id="LI001", product_code="SKU123", quantity=50)
        >>> artwork = Artwork(
        ...     artwork_id="ART123",
        ...     line_item_id=str(line_item.id),
        ...     design_url="https://example.com/design",
        ...     design_paths=[Path("design.pdf")],
        ...     placement_url="https://example.com/placement",
        ...     placement_path=Path("placement.pdf"),
        ... )
        >>> line_item.set_artwork(artwork)
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    remote_line_id: str
    product_code: str
    quantity: int
    artwork: Artwork | None = None

    def __post_init__(self) -> None:
        """Validate and normalize all line item fields after initialization.

        This method is called automatically by the dataclass decorator after
        the instance is created. It validates each field according to domain
        rules and normalizes string values. All validations must pass before
        the object is considered fully initialized.

        Validation steps performed:
        1. remote_line_id: non-empty string, normalized (whitespace trimmed)
        2. product_code: non-empty string, normalized (whitespace trimmed)
        3. quantity: positive integer (>0)
        4. artwork: None or Artwork instance

        Raises:
            ValueError: If remote_line_id is empty or not a string
            ValueError: If product_code is empty or not a string
            ValueError: If quantity is not positive
            ValueError: If artwork is not None and not an Artwork instance
        """
        validators.validate_non_empty_string(self.remote_line_id, "Remote line ID")
        validators.set_normalized_string(self, "remote_line_id", self.remote_line_id)

        validators.validate_non_empty_string(self.product_code, "Product code")
        validators.set_normalized_string(self, "product_code", self.product_code)

        validators.validate_positive_int(self.quantity, "Quantity")

        # artwork is optional, but if provided must be an Artwork instance
        if self.artwork is not None and not isinstance(self.artwork, Artwork):
            raise ValueError("Artwork must be an instance of Artwork or None")

    def set_artwork(self, artwork: Artwork) -> None:
        """Assign artwork specifications to this line item.

        This method allows setting or updating the artwork for the line item
        after initialization. The artwork must be a valid Artwork instance.
        Despite the class being frozen, this method uses object.__setattr__
        to modify the artwork field, as permitted for specific domain operations.

        Args:
            artwork: An Artwork instance containing design specifications.
                     Cannot be None.

        Raises:
            ValueError: If artwork is not an Artwork instance.

        Example:
            >>> line_item.set_artwork(artwork_instance)
        """
        if not isinstance(artwork, Artwork):
            raise ValueError("Artwork must be an instance of Artwork")
        object.__setattr__(self, "artwork", artwork)
