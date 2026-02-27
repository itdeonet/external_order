""" "Stock Transfer Service Interface"""

from collections.abc import Generator
from typing import Any, Protocol

from src.interfaces.ierror_queue import IErrorQueue


class IStockService(Protocol):
    """Interface for stock transfer services."""

    def read_stock_transfers(
        self, error_queue: IErrorQueue
    ) -> Generator[dict[str, Any], None, None]:
        """Read stock transfer requests."""
        ...

    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Reply to stock transfer requests."""
        ...
