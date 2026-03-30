"""Harman-specific order processing service.

Provides `HarmanOrderService` for parsing Harman EDIFACT orders, creating
`Order` models, persisting them, and generating completion notifications.
"""

import datetime as dt
import itertools
import json
import random
import re
import string
from collections.abc import Generator
from dataclasses import asdict, dataclass, field
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Any

from pydifact import Parser, Segment, Serializer  # type: ignore

from src.app.errors import NotifyError, get_error_store
from src.app.registry import get_artwork_services, get_order_services
from src.config import Config, get_config
from src.domain import (
    Artwork,
    IArtworkService,
    ISaleService,
    LineItem,
    Order,
    OrderStatus,
    ShipTo,
)
from src.services.render_service import RenderService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanOrderService:
    """Service to parse Harman EDIFACT orders and manage their lifecycle.

    Configuration-driven; integrates with `RenderService` and `ErrorStore`.
    """

    artwork_service: IArtworkService | None
    name_filter: str
    order_provider: str
    administration_id: int = field(default_factory=lambda: get_config().harman_administration_id)
    customer_id: int = field(default_factory=lambda: get_config().harman_customer_id)
    pricelist_id: int = field(default_factory=lambda: get_config().harman_pricelist_id)
    shipment_type: str = field(default_factory=lambda: get_config().harman_shipment_type)
    workdays_for_delivery: int = field(
        default_factory=lambda: get_config().harman_workdays_for_delivery
    )
    input_dir: Path = field(default_factory=lambda: Path(get_config().harman_input_dir))
    output_dir: Path = field(default_factory=lambda: Path(get_config().harman_output_dir))
    renderer: RenderService = field(default_factory=lambda: RenderService())

    @classmethod
    def register(cls, name: str, artwork_provider: str, name_filter: str) -> None:
        """Factory method to create and register a HarmanOrderService instance."""
        logger.info("Register HarmanOrderService with name '%s'", name)
        artwork_service = get_artwork_services().get(artwork_provider)
        if artwork_provider and not artwork_service:
            raise ValueError(f"Artwork service '{artwork_provider}' not found in registry")
        order_service = cls(
            artwork_service=artwork_service, order_provider=name, name_filter=name_filter
        )
        get_order_services().register(name, order_service)

    def read_orders(self) -> Generator[Order, None, None]:
        """Parse EDIFACT files and yield Order instances.

        Scans input_dir for order files (*.insdes, *.new, *.created, *.artwork),
        parses each into structured data, and yields Order instances.

        Yields:
            Order: Parsed order from each input file.

        Note:
            Parsing errors are recorded in ErrorStore and do not stop iteration.
        """
        logger.info("Generate orders...")
        # parse each .insdes file in the directory and yield an Order instance
        chain = itertools.chain.from_iterable(
            [
                self.input_dir.glob("*.new", case_sensitive=False),
                self.input_dir.glob("*.created", case_sensitive=False),
                self.input_dir.glob("*.artwork", case_sensitive=False),
                self.input_dir.glob("*.insdes", case_sensitive=False),
            ]
        )
        for file in chain:
            if not re.match(self.name_filter, file.stem, re.IGNORECASE):
                continue
            try:
                logger.info("Process file: %s", file)
                order_data = self._read_order_data(file)
                yield self._make_order(order_data)
            except Exception as exc:
                logger.error("Failed to process file: %s", file, exc_info=exc)
                get_error_store().add(exc)

    def _read_order_data(self, file: Path) -> dict[str, Any]:
        """Parse EDIFACT file and extract structured order data.

        Args:
            file: Path to EDIFACT order file.

        Returns:
            Dict with 'ship_to' and 'line_items' keys extracted from file.
        """
        order_data: dict[str, Any] = {
            "ship_to": {},
            "line_items": [],
        }
        for segment in Parser().parse(file.read_text(encoding="utf-8")):
            # extract data from the segment and update the order data
            self._get_segment_data(segment, order_data)
        logger.info("Extracted order data: %s", order_data)
        return order_data

    def _get_segment_data(self, segment: Segment, order_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single EDIFACT `segment` and update `order_data` in-place."""
        logger.debug("Process segment: %s", segment)
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
            case ["RFF", ["DQ", delivery_note_id]]:
                order_data["delivery_note_id"] = delivery_note_id
            case ["RFF", ["ON", remote_order_id]]:
                order_data["remote_order_id"] = remote_order_id
            case ["LIN", line_id, "1", [product_code, "MF"]]:
                order_data["line_items"].append(
                    {"remote_line_id": line_id, "product_code": product_code}
                )
            case ["QTY", ["113", quantity, unit_of_measure]]:
                assert order_data["line_items"], "QTY segment must be preceded by a LIN segment."
                order_data["line_items"][-1]["quantity"] = int(quantity)
                order_data["line_items"][-1]["unit_of_measure"] = unit_of_measure
            case ["FTX", "DEL", "3", "", delivery_instructions]:
                order_data["delivery_instructions"] = delivery_instructions
            case ["FTX", "PRD", "", "", [location, stock_status]]:
                assert order_data["line_items"], "FTX segment must be preceded by a LIN segment."
                order_data["line_items"][-1]["location"] = location
                order_data["line_items"][-1]["stock_status"] = stock_status

        logger.debug("Updated order data: %s", order_data)
        return order_data

    def _make_order(self, data: dict[str, Any]) -> Order:
        """Create Order domain model from parsed EDIFACT data.

        Args:
            data: Structured order data from _read_order_data.

        Returns:
            Order instance with ShipTo and LineItems populated from data.
        """
        logger.info("Create Order instance from order_data")
        is_company = bool(data.get("ship_to", {}).get("company_name"))
        ship_to_data = data.get("ship_to", {})
        order = Order(
            administration_id=self.administration_id,
            customer_id=self.customer_id,
            order_provider=self.order_provider,
            pricelist_id=self.pricelist_id,
            remote_order_id=data.get("remote_order_id", ""),
            shipment_type=f"{self.shipment_type}{'b2b%' if is_company else 'b2c%'}",
            description=(
                f"{self.order_provider} order {data.get('remote_order_id', '')}"
                f" / {data.get('delivery_note_id', '')}"
            ),
            delivery_instructions=data.get("delivery_instructions", ""),
            ship_to=ShipTo(
                remote_customer_id=ship_to_data.get("remote_customer_id", ""),
                company_name=ship_to_data.get("company_name", ""),
                contact_name=ship_to_data.get("contact_name", ""),
                email=ship_to_data.get("email", ""),
                phone=ship_to_data.get("phone", ""),
                street1=ship_to_data.get("street1", ""),
                street2=ship_to_data.get("street2", ""),
                city=ship_to_data.get("city", ""),
                state=ship_to_data.get("state", ""),
                postal_code=ship_to_data.get("postal_code", ""),
                country_code=ship_to_data.get("country_code", ""),
            ),
            line_items=[
                LineItem(
                    line_id=item.get("remote_line_id", ""),
                    product_code=item.get("product_code", ""),
                    quantity=int(item.get("quantity", 0)),
                )
                for item in data.get("line_items", [])
            ],
        )

        order.set_ship_at(Order.calculate_delivery_date(self.workdays_for_delivery))
        return order

    def read_order_data_by_remote_order_id(self, remote_order_id: str) -> dict[str, Any] | None:
        """Find and parse the file for `remote_order_id`, returning parsed data."""
        logger.info("Get order data for remote order ID: %s", remote_order_id)
        for file in self.input_dir.glob(f"{remote_order_id}.*", case_sensitive=False):
            if file.suffix.lower() == ".json":
                continue  # skip JSON files
            return self._read_order_data(file)
        return None

    def should_update_sale(self, order: Order) -> bool:
        """Determine if an existing sale should be updated based on remote_order_id."""
        logger.info("Check if sale should be updated for order: %s", order.remote_order_id)
        return "B2B" in self.order_provider.upper()

    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Persist `order` as JSON in `input_dir` and update file status."""
        logger.info("Persist order: %s with status: %s", order.remote_order_id, status)

        def custom_serializer(obj):
            if isinstance(obj, dt.datetime):
                return obj.isoformat()
            if isinstance(obj, dt.date):
                return obj.isoformat()
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")

        # update the order status and persist as JSON
        order.set_status(status)
        order_data = asdict(order)
        file_path = self.input_dir / f"{order.remote_order_id}.json"
        text = json.dumps(order_data, indent=4, ensure_ascii=False, default=custom_serializer)
        file_path.write_text(text, encoding="utf-8")

        # rename the INSDES file to reflect the new status
        for file in self.input_dir.glob(f"{order.remote_order_id}.*"):
            if file.suffix.lower() != ".json":
                file.rename(file.parent / f"{order.remote_order_id}.{order.status.value}".upper())

    def load_order(self, remote_order_id: str) -> Order:
        """Load and return an `Order` previously persisted as JSON."""
        logger.info("Load order by remote ID: %s", remote_order_id)
        file_path = self.input_dir / f"{remote_order_id}.json"
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)

        # pop all non init fields and prepare the data for Order initialization
        sale_id = data.pop("sale_id", 0)
        sale_name = data.pop("sale_name", "")
        status = data.pop("status", OrderStatus.NEW.value)
        created_at = dt.datetime.fromisoformat(
            data.pop("created_at", (dt.datetime.now() - dt.timedelta(days=2)).isoformat())
        )
        data.pop("ship_at", None)  # ship_at will be current date
        ship_at = dt.date.today()

        # convert ship_to and line_items back to their respective domain models
        data["ship_to"] = ShipTo(**data.get("ship_to", {}))
        items = []
        for item in data.get("line_items", []):
            artwork_data: dict[str, Any] = item.pop("artwork", {})
            item["artwork"] = (
                Artwork(
                    artwork_id=artwork_data.get("artwork_id", ""),
                    artwork_line_id=artwork_data.get("artwork_line_id", ""),
                    design_url=artwork_data.get("design_url", ""),
                    design_paths=[Path(p) for p in artwork_data.get("design_paths", [])],
                    placement_url=artwork_data.get("placement_url", ""),
                    placement_path=Path(artwork_data.get("placement_path", "")),
                )
                if artwork_data
                else None
            )
            item = LineItem(**item)
            items.append(item)
        data["line_items"] = items

        order = Order(**data)
        if sale_id > 0:
            order.set_sale_id(sale_id)
        if sale_name:
            order.set_sale_name(sale_name)
        order.set_status(OrderStatus(status))
        order.set_created_at(created_at)
        order.set_ship_at(ship_at)
        return order

    def notify_completed_sale(self, order: Order, notify_data: dict[str, Any]) -> None:
        """Notify Harman of a completed sale by generating DESADV messages.

        Creates delivery advice (DESADV) notifications in both D96A and D99A
        EDIFACT format. Uses Jinja2 templates to generate the EDI messages
        and the PYDIFACT library to serialize them properly.

        Two files are created in the output directory:
        - {remote_order_id}.DESADVD96A (legacy format)
        - {remote_order_id}.DESADVD99A (current format)

        Args:
            order: The Order instance that has been completed
            notify_data: The data used to generate the notification
        Raises:
            NotifyError: If required order data cannot be found
            May raise exceptions if file writing fails
        """
        logger.info("Notify completed sale for order: %s", order.remote_order_id)
        # The notification exists of 2 desdav files, one in D96A format and one in D99A format.
        for file in self.renderer.directory.glob("desadv*.j2"):
            # build the notification message using the renderer and clean it up
            message = self.renderer.render(file.name, notify_data)
            segments = Parser().parse(message)
            content = Serializer().serialize(list(segments), break_lines=True)

            # write the message
            notify_path = self.output_dir / f"{order.remote_order_id}.{file.stem}".upper()
            notify_path.write_text(content, encoding="utf-8")

    def get_notify_data(self, order: Order, sale_service: ISaleService) -> dict[str, Any]:
        """Get the data needed for DESADV notification generation.

        Prepares all data required to render DESADV notification templates,
        including order information, shipment details, and EDI segment counts.
        Different segment counts are calculated for D96A vs D99A formats.

        Args:
            order: The Order being notified about
            sale_service: The service used to interact with sales data

        Returns:
            Dictionary with notification data for template rendering:
            - interchange_control_ref: Unique message reference
            - ship_date, expected_date: Shipment timeline
            - box dimensions and SSCC: Shipment details
            - segments: Calculated EDI segment count
            - order: Original parsed order data

        Raises:
            NotifyError: If required order data cannot be retrieved
        """
        logger.info("Get notify data for order: %s", order.remote_order_id)

        # get info from INSDES file to include in the notification
        order_data = self.read_order_data_by_remote_order_id(order.remote_order_id)
        if not (order_data and order_data.get("ship_to") and order_data.get("line_items")):
            raise NotifyError("No valid order data found", order_id=order.remote_order_id)

        num_segments = {
            "D96A": sum(
                [
                    # header and trailer segements
                    35,
                    # segments per line item: 4 fixed
                    4 * len(order_data["line_items"]),
                    # serial segments per quantity: 1 per quantity unit
                    sum(item.get("quantity", 0) for item in order_data["line_items"]),
                    # PCI segments: 1 per 10 products, at least 1
                    1,
                    sum(item.get("quantity", 0) for item in order_data["line_items"]) // 10,
                ]
            ),
            "D99A": sum(
                [
                    # header and trailer segments
                    9,
                    # segments per line item: 4 fixed
                    4 * len(order_data["line_items"]),
                    # serial segments per quantity: 1 per quantity unit
                    sum(item.get("quantity", 0) for item in order_data["line_items"]),
                    # FTX segments: 1
                    1,
                ]
            ),
        }

        config: Config = get_config()
        box_length, box_width, box_height = config.default_box_size
        notify_data = {
            "interchange_control_ref": "".join(random.choices(string.digits, k=10)),
            "ship_date": dt.datetime.now(dt.UTC),
            "expected_date": dt.datetime.now(dt.UTC) + dt.timedelta(days=2),
            "box_length": box_length,
            "box_width": box_width,
            "box_height": box_height,
            "sale_name": order.sale_name,
            "sscc": "".join(random.choices(string.digits, k=20)),
            "num_segments": num_segments,
            "order": order_data,
        }

        # get shipping info and serials from the sale service to include in the notification
        shipping_info: dict[str, Any] = sale_service.search_shipping_info(order)[0]
        carrier_tracking_ref = shipping_info["carrier_tracking_ref"].split(", ")
        shipping_info["carrier_tracking_ref"] = carrier_tracking_ref
        notify_data["shipping_info"] = shipping_info
        notify_data["serials_by_line"] = sale_service.search_serials_by_line_item(order)

        return notify_data
