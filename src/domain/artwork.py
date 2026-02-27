"""Represents the artwork for a line item in an order."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class Artwork:
    """Represents the artwork for a line item in an order."""

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    artwork_id: str
    line_item_id: str
    design_url: str
    design_paths: list[Path]
    placement_url: str
    placement_path: Path

    def __post_init__(self) -> None:
        """Post-initialization processing."""
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
