"""Harman order service implementation."""

import datetime as dt
import json
import random
import re
import string
from collections.abc import Generator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Self

from pydifact import Parser, Segment, Serializer  # type: ignore

from src.app.errors import NotifyError
from src.config import Config
from src.domain.line_item import LineItem
from src.domain.order import Order, OrderStatus
from src.domain.ship_to import ShipTo
from src.interfaces.iartwork_service import IArtworkService
from src.interfaces.ierror_queue import IErrorQueue
from src.interfaces.iregistry import IRegistry
from src.services.render_service import RenderService


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanOrderService:
    """Harman order service implementation."""

    administration_id: int
    customer_id: int
    pricelist_id: int
    order_provider: str
    shipment_type: str
    workdays_for_delivery: int
    input_orders_dir: Path
    json_orders_dir: Path
    notify_dir: Path
    renderer: RenderService

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create a HarmanOrderService instance from settings."""
        return cls(
            administration_id=config.harman_administration_id,
            customer_id=config.harman_customer_id,
            pricelist_id=config.harman_pricelist_id,
            order_provider=config.harman_order_provider,
            shipment_type=config.harman_shipment_type,
            workdays_for_delivery=config.harman_workdays_for_delivery,
            input_orders_dir=config.harman_input_orders_dir,
            json_orders_dir=config.json_orders_dir,
            notify_dir=config.harman_notify_dir,
            renderer=RenderService(directory=config.templates_dir),
        )

    def get_orders(self, error_queue: IErrorQueue) -> Generator[Order, None, None]:
        """Generate orders."""
        # parse each .insdes file in the directory and yield an Order instance
        for file in self.input_orders_dir.glob("*.insdes", case_sensitive=False):
            try:
                order_data = self._get_order_data(file)
                yield self._make_order(order_data)
            except Exception as exc:
                error_queue.put(exc)

    def _get_order_data(self, file: Path) -> dict[str, Any]:
        """Extract order data from the given file."""
        order_data: dict[str, Any] = {
            "ship_to": {},
            "line_items": [],
        }
        for segment in Parser().parse(file.read_text(encoding="utf-8")):
            # extract data from the segment and update the order data
            self._get_segment_data(segment, order_data)
        return order_data

    def _get_segment_data(self, segment: Segment, order_data: dict[str, Any]) -> dict[str, Any]:
        """Extract data from a segment."""
        match [segment.tag, *segment.elements]:
            case [
                "NAD",
                "ST",
                remote_customer_id,
                [name1, name2, email, *_],
                [phone, *_],
                [street1, street2, _, house_nr, *_],
                city,
                state,
                postcode,
                country,
            ]:
                order_data["ship_to"]["remote_customer_id"] = remote_customer_id
                order_data["ship_to"]["company_name"] = name1 if name2 else ""
                order_data["ship_to"]["contact_name"] = name2 if name2 else name1
                order_data["ship_to"]["email"] = email
                order_data["ship_to"]["phone"] = phone
                order_data["ship_to"]["street1"] = f"{street1} {house_nr}".strip()
                order_data["ship_to"]["street2"] = street2
                order_data["ship_to"]["city"] = city
                order_data["ship_to"]["state"] = state
                order_data["ship_to"]["postal_code"] = postcode
                order_data["ship_to"]["country_code"] = country
            case ["RFF", "DQ", delivery_note_id]:
                order_data["delivery_note_id"] = delivery_note_id
            case ["RFF", "ON", remote_order_id]:
                order_data["remote_order_id"] = remote_order_id
            case ["LIN", id, "1", [product_code, "MF"]]:
                order_data["line_items"].append(
                    {"remote_line_id": id, "product_code": product_code}
                )
            case ["QTY", "113", quantity, unit_of_measure]:
                assert order_data["line_items"], "QTY segment must be preceded by a LIN segment."
                order_data["line_items"][-1]["quantity"] = quantity
                order_data["line_items"][-1]["unit_of_measure"] = unit_of_measure
            case ["FTX", "PRD", "", "", [location, stock_status]]:
                assert order_data["line_items"], "FTX segment must be preceded by a LIN segment."
                order_data["line_items"][-1]["location"] = location
                order_data["line_items"][-1]["stock_status"] = stock_status

        return order_data

    def _make_order(self, data: dict[str, Any]) -> Order:
        """Create an Order instance from the given data."""
        is_company = bool(data.get("ship_to", {}).get("company_name"))
        order = Order(
            administration_id=self.administration_id,
            customer_id=self.customer_id,
            order_provider=self.order_provider,
            pricelist_id=self.pricelist_id,
            remote_order_id=data.get("remote_order_id", ""),
            shipment_type=f"{self.shipment_type}{'b2b%' if is_company else 'b2c%'}",
            ship_to=ShipTo(
                remote_customer_id=data.get("ship_to", {}).get("remote_customer_id", ""),
                company_name=data.get("ship_to", {}).get("company_name", ""),
                contact_name=data.get("ship_to", {}).get("contact_name", ""),
                email=data.get("ship_to", {}).get("email", ""),
                phone=data.get("ship_to", {}).get("phone", ""),
                street1=data.get("ship_to", {}).get("street1", ""),
                street2=data.get("ship_to", {}).get("street2", ""),
                city=data.get("ship_to", {}).get("city", ""),
                state=data.get("ship_to", {}).get("state", ""),
                postal_code=data.get("ship_to", {}).get("postal_code", ""),
                country_code=data.get("ship_to", {}).get("country_code", ""),
            ),
            line_items=[
                LineItem(
                    remote_line_id=item.get("id", ""),
                    product_code=item.get("product_code", ""),
                    quantity=int(item.get("quantity", 0)),
                )
                for item in data.get("line_items", [])
            ],
        )

        order.set_ship_at(Order.calculate_delivery_date(self.workdays_for_delivery))
        return order

    def get_order_data_by_remote_order_id(self, remote_order_id: str) -> dict[str, Any] | None:
        """Get order data by remote ID."""
        for file in self.input_orders_dir.glob(f"{remote_order_id}.*"):
            return self._get_order_data(file)
        return None

    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Get the artwork service for the given order."""
        if re.match(r"(HA|JB)-EM-(ST-)?\d+", order.remote_order_id):
            return artwork_services.get("Spectrum")
        return None

    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Save the given order."""

        def custom_serializer(obj):
            if isinstance(obj, dt.datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        order.set_status(status)
        order_data = asdict(order)
        file_path = self.json_orders_dir / f"{order.remote_order_id}.json"
        text = json.dumps(order_data, indent=4, ensure_ascii=False, default=custom_serializer)
        file_path.write_text(text, encoding="utf-8")

        for file in self.input_orders_dir.glob(f"{order.remote_order_id}.*"):
            file.rename(file.parent / f"{order.remote_order_id}.{order.status.value}".upper())

    def load_order(self, remote_order_id: str) -> Order | None:
        """Load an order by remote ID."""
        file_path = self.json_orders_dir / f"{remote_order_id}.json"
        if not file_path.exists():
            return None
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)
        return Order(**data)

    def notify_completed_sale(self, order: Order) -> None:
        """Notify the order provider of a completed sale."""
        for file in self.renderer.directory.glob("desadv-*.j2"):
            doc_type = "D96A" if "D96A" in file.name.upper() else "D99A"
            notify_data = self._get_notify_data(order, doc_type)
            message = self.renderer.render(file.name, notify_data)
            segments = Parser().parse(message)
            content = Serializer().serialize(list(segments), break_lines=True)
            notify_path = (
                self.notify_dir / file.stem / f"{order.remote_order_id}.{file.stem}".upper()
            )
            notify_path.write_text(content, encoding="utf-8")

    def _get_notify_data(self, order: Order, doc_type: str) -> dict[str, Any]:
        """Get the data needed for the notification."""
        order_data = self.get_order_data_by_remote_order_id(order.remote_order_id)
        if not (order_data and order_data.get("ship_to") and order_data.get("line_items")):
            raise NotifyError("No valid order data found", order_id=order.remote_order_id)

        segments_d96a = [
            35,  # Header and trailer segments
            4 * len(order_data["line_items"]),  # Segments per line item
            sum(item.get("quantity", 0) for item in order_data["line_items"]),  # Serial segments
            1
            + sum(item.get("quantity", 0) for item in order_data["line_items"])
            // 10,  # PCI segments (1 per 10 products)
        ]
        segments_d99a = [
            9,  # Header and trailer segments
            4 * len(order_data["line_items"]),  # Segments per item
            sum(item.get("quantity", 0) for item in order_data["line_items"]),  # Serial segments
            1,  # FTX segment
        ]
        notify_data = {
            "interchange_control_ref": "".join(random.choices(string.digits, k=10)),
            "ship_date": dt.datetime.now(dt.UTC),
            "expected_date": dt.datetime.now(dt.UTC) + dt.timedelta(days=2),
            "box_length": 24,
            "box_width": 21,
            "box_height": 6,
            "sscc": "".join(random.choices(string.digits, k=20)),
            "segments": sum(segments_d96a) if doc_type == "D96A" else sum(segments_d99a),
            "item_description": "CLEAR",
            "order": order_data,
        }
        return notify_data
