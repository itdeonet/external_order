"""A line item in an order."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class LineItem:
    """A line item in an order."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    quantity: int
    artwork_id: str = ""
    design_url: str = field(default="", init=False)
    design_paths: list[Path] = field(default_factory=list, init=False)
    placement_url: str = field(default="", init=False)
    placement_path: Path = field(default=Path(""), init=False)

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if not (isinstance(self.id, str) and self.id.strip()):
            raise ValueError("ID must be a non-empty string")
        object.__setattr__(self, "id", self.id.strip())

        if not (isinstance(self.product_id, str) and self.product_id.strip()):
            raise ValueError("Product ID must be a non-empty string")
        object.__setattr__(self, "product_id", self.product_id.strip())

        if not (isinstance(self.quantity, int) and self.quantity > 0):
            raise ValueError("Quantity must be a positive integer")

        if not (isinstance(self.artwork_id, str) and self.artwork_id.strip()):
            object.__setattr__(self, "artwork_id", "")
        object.__setattr__(self, "artwork_id", self.artwork_id.strip())

    def set_id(self, id: str) -> None:
        """Set the ID for the line item."""
        if not (isinstance(id, str) and id.strip()):
            raise ValueError("ID must be a non-empty string")
        object.__setattr__(self, "id", id.strip())

    def set_artwork_id(self, artwork_id: str) -> None:
        """Set the artwork ID for the line item."""
        if not (isinstance(artwork_id, str) and artwork_id.strip()):
            raise ValueError("Artwork ID must be a non-empty string")
        object.__setattr__(self, "artwork_id", artwork_id.strip())

    def set_design(self, url: str, paths: list[Path]) -> None:
        """Set the design URL and its corresponding file paths for the line item."""
        if not (isinstance(url, str) and url.strip()):
            raise ValueError("Design URL must be a non-empty string")
        object.__setattr__(self, "design_url", url.strip())

        if not (
            isinstance(paths, list)
            and all(isinstance(path, Path) and path.is_file() for path in paths)
        ):
            raise ValueError("Design paths must be a list of valid file paths")
        object.__setattr__(self, "design_paths", paths)

    def set_placement(self, url: str, path: Path) -> None:
        """Set the placement URL and its corresponding file path for the line item."""
        if not (isinstance(url, str) and url.strip()):
            raise ValueError("Placement URL must be a non-empty string")
        object.__setattr__(self, "placement_url", url.strip())

        if not (isinstance(path, Path) and path.is_file()):
            raise ValueError("Placement path must be a valid file path")
        object.__setattr__(self, "placement_path", path)

    def has_artwork(self) -> bool:
        """Check if the line item has artwork associated with it."""
        return (
            bool(self.artwork_id)
            and bool(self.design_url)
            and bool(self.design_paths)
            and bool(self.placement_url)
            and bool(self.placement_path)
        )
