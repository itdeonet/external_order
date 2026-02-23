"""Artwork service interface."""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.domain.order import Order


class IArtworkService(Protocol):
    """Interface for artwork services."""

    def get_artwork(self, order: "Order") -> list[Path]:
        """Get artwork data for the given order."""
        ...
