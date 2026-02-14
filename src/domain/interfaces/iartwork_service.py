"""Artwork service interface."""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.domain.order import Order


@runtime_checkable
class IArtworkService(Protocol):
    """Interface for artwork services."""

    def get_artwork(self, order: "Order") -> list[Path]:
        """Get artwork data for the given order."""
        ...
