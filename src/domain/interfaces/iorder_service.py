"""Order service interface."""

from collections.abc import Generator
from dataclasses import asdict
import datetime as dt
import json
from pathlib import Path
from typing import Protocol

from src.app.registry import Registry
from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.interfaces.ierror_queue import IErrorQueue
from src.domain.order import Order


class IOrderService(Protocol):
    """Interface for order services."""

    def get_orders(self, directory: Path, error_queue: IErrorQueue) -> Generator[Order, None, None]:
        """Generate orders."""
        ...

    def get_artwork_service(
        self, order: Order, artwork_services: Registry[IArtworkService]
    ) -> IArtworkService | None:
        """Get the artwork service for the given order."""
        ...

    def save_order(self, order: Order, directory: Path) -> None:
        """Save the given order."""

        def custom_serializer(obj):
            if isinstance(obj, dt.datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        order_name = f"S{order.id:05}.json" if order.id else f"{order.remote_order_id}.json"
        file_path = directory / order_name
        order_data = asdict(order)
        text = json.dumps(order_data, indent=4, ensure_ascii=False, default=custom_serializer)
        file_path.write_text(text, encoding="utf-8")
