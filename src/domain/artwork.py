"""Domain model for artwork associated with order line items.

This module defines the Artwork class, which represents digital artwork files
and metadata for a specific line item in an order. Artwork is immutable and
requires validation of all file paths and URLs at construction time.

Validation ensures:
- All string fields are non-empty after stripping whitespace
- All Path fields point to existing files on disk
- Data integrity is maintained throughout the object's lifetime
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class Artwork:
    """Immutable artwork model for a line item in an order.

    This frozen dataclass represents the artwork files and metadata associated
    with a specific line item. All fields are validated during post-initialization
    to ensure data consistency. The id field is auto-generated per instance and
    cannot be modified after construction.

    This class enforces:
    - Immutability: All attributes are read-only after object creation
    - Validation: All fields must meet strict requirements
    - File existence: Design and placement paths must point to existing files
    - URL validity: Design and placement URLs must be non-empty strings

    Attributes:
        id: Unique auto-generated UUID for this artwork instance
        artwork_id: External identifier for the artwork in the order service
        line_item_id: Reference to the parent line item
        design_url: URL where the design file can be accessed
        design_paths: List of Path objects pointing to local design files
        placement_url: URL where the placement specification can be accessed
        placement_path: Path to the local placement specification file

    Example:
        >>> from pathlib import Path
        >>> design_file = Path("/tmp/design.pdf")
        >>> design_file.write_text("design data")
        >>> placement_file = Path("/tmp/placement.pdf")
        >>> placement_file.write_text("placement data")
        >>> artwork = Artwork(
        ...     artwork_id="ART123",
        ...     line_item_id="LI456",
        ...     design_url="https://example.com/design",
        ...     design_paths=[design_file],
        ...     placement_url="https://example.com/placement",
        ...     placement_path=placement_file,
        ... )
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    artwork_id: str
    line_item_id: str
    design_url: str
    design_paths: list[Path]
    placement_url: str
    placement_path: Path

    def __post_init__(self) -> None:
        """Validate and normalize all artwork fields after initialization.

        This method is called automatically by the dataclass decorator after
        the instance is created. It validates each field and normalizes string
        values by stripping whitespace. All validations must pass before the
        object is considered fully initialized.

        Validation steps performed:
        1. artwork_id: must be a non-empty string (after stripping)
        2. line_item_id: must be a non-empty string (after stripping)
        3. design_url: must be a non-empty string (after stripping)
        4. design_paths: must be a non-empty list of existing Path objects
        5. placement_url: must be a non-empty string (after stripping)
        6. placement_path: must be an existing Path object

        Raises:
            ValueError: If artwork_id is empty or not a string
            ValueError: If line_item_id is empty or not a string
            ValueError: If design_url is empty or not a string
            ValueError: If design_paths is not a list of existing Path objects
            ValueError: If placement_url is empty or not a string
            ValueError: If placement_path is not an existing Path object
        """
        if not (isinstance(self.artwork_id, str) and self.artwork_id.strip()):
            raise ValueError("Artwork ID must be a non-empty string")
        object.__setattr__(self, "artwork_id", self.artwork_id.strip())

        if not (isinstance(self.line_item_id, str) and self.line_item_id.strip()):
            raise ValueError("Line item ID must be a non-empty string")
        object.__setattr__(self, "line_item_id", self.line_item_id.strip())

        if not (isinstance(self.design_url, str) and self.design_url.strip()):
            raise ValueError("Design URL must be a non-empty string")
        object.__setattr__(self, "design_url", self.design_url.strip())

        if not (
            self.design_paths
            and isinstance(self.design_paths, list)
            and all(isinstance(p, Path) and p.is_file() for p in self.design_paths)
        ):
            raise ValueError("Design paths must be a list of Path objects")

        if not (isinstance(self.placement_url, str) and self.placement_url.strip()):
            raise ValueError("Placement URL must be a non-empty string")
        object.__setattr__(self, "placement_url", self.placement_url.strip())

        if not (isinstance(self.placement_path, Path) and self.placement_path.is_file()):
            raise ValueError("Placement path must be a Path object")
