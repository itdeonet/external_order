"""Harman order service implementation."""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Self

from pydifact import Parser, Segment  # type: ignore

from src.app.registry import Registry
from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.interfaces.ierror_queue import IErrorQueue
from src.domain.interfaces.iorder_service import IOrderService
from src.domain.line_item import LineItem
from src.domain.order import Order
from src.domain.ship_to import ShipTo
from src.settings import Settings


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanOrderService(IOrderService):
    """Harman order service implementation."""

    administration_id: int
    customer_id: int
    pricelist_id: int
    order_provider: str
    shipment_type: str
    workdays_for_delivery: int
    input_orders_dir: Path
    json_orders_dir: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """Create a HarmanOrderService instance from settings."""
        return cls(
            administration_id=settings.harman_administration_id,
            customer_id=settings.harman_customer_id,
            pricelist_id=settings.harman_pricelist_id,
            order_provider=settings.harman_order_provider,
            shipment_type=settings.harman_shipment_type,
            workdays_for_delivery=settings.harman_workdays_for_delivery,
            input_orders_dir=settings.harman_input_orders_dir,
            json_orders_dir=settings.json_orders_dir,
        )

    def get_orders(self, error_queue: IErrorQueue) -> Generator[Order, None, None]:
        """Generate orders."""
        # parse each .insdes file in the directory and yield an Order instance
        for file in self.input_orders_dir.glob("*.insdes", case_sensitive=False):
            try:
                order_data: dict[str, Any] = {
                    "ship_to": {},
                    "line_items": [],
                }
                for segment in Parser().parse(file.read_text(encoding="utf-8")):
                    # extract data from the segment and update the order data
                    self._get_segment_data(segment, order_data)

                yield self._make_order(order_data)
            except Exception as exc:
                error_queue.put(exc)

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
            case ["LIN", id, "1", [product_id, "MF"]]:
                order_data["line_items"].append({"id": id, "product_id": product_id})
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
                    id=item.get("id", ""),
                    product_id=item.get("product_id", ""),
                    quantity=int(item.get("quantity", 0)),
                )
                for item in data.get("line_items", [])
            ],
        )

        order.set_ship_at(Order.calculate_delivery_date(self.workdays_for_delivery))
        return order

    def get_artwork_service(
        self, order: Order, artwork_services: Registry[IArtworkService]
    ) -> IArtworkService | None:
        """Get the artwork service for the given order."""
        if re.match(r"(HA|JB)-EM-(ST-)?\d+", order.remote_order_id):
            return artwork_services.get("Spectrum")
        return None
