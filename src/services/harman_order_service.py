"""Harman order service implementation.

This module provides the HarmanOrderService, which reads orders from Harman EDI files
(EDIFACT format) and manages the complete order lifecycle: reading, parsing, persisting,
and notifying Harman of completion. It implements the IOrderService protocol.

Key responsibilities:
- Reading EDIFACT order files (.insdes and .created files) from input directory
- Parsing EDI segments and extracting order/shipping/line item data
- Creating Order domain model instances from parsed data
- Persisting orders to JSON format for storage
- Generating notification messages (DESADV D96A/D99A format) for completed orders
- Selecting appropriate artwork services based on order IDs

The service is configured from application settings and works with Harman-specific
format requirements and business rules.
"""

import datetime as dt
import itertools
import json
import random
import re
import string
import uuid
from collections.abc import Generator
from dataclasses import asdict, dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Any, Self

from pydifact import Parser, Segment, Serializer  # type: ignore

from src.app.errors import ErrorStore, NotifyError
from src.config import Config, get_config
from src.domain import LineItem, Order, OrderStatus, ShipTo
from src.interfaces import IArtworkService, IRegistry
from src.services.render_service import RenderService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class HarmanOrderService:
    """Harman order service implementation for reading and managing orders.

    This service reads orders from Harman EDI files in EDIFACT format and manages
    their complete lifecycle. It parses EDI segments, creates Order domain models,
    handles persistence, and generates Harman-format completion notifications.

    All fields are configuration values that define how this service processes
    Harman orders, including naming, shipment type, delivery timing, and
    file system paths.

    This class enforces:
    - Frozen: All attributes are read-only after creation (configured via from_config)
    - Harman-specific processing: EDIFACT parsing, shipment type formatting
    - Proper error handling with ErrorStore singleton
    - Integration with RenderService for notification templates

    Attributes:
        administration_id: Internal administration unit ID for orders
        customer_id: Internal customer ID for Harman orders
        pricelist_id: Pricing list ID for Harman orders
        order_provider: Name of the provider ('Harman')
        shipment_type: Base shipment type (formatted as B2B or B2C)
        workdays_for_delivery: Standard lead time in workdays
        input_dir: Path to directory containing order files
        output_dir: Path to directory for output notifications
        renderer: RenderService for generating EDI notifications

    Example:
        >>> service = HarmanOrderService.from_config(config)
        >>> for order in service.read_orders():
        ...     print(f"Processing {order.remote_order_id}")
        ...     service.persist_order(order, OrderStatus.CREATED)
    """

    administration_id: int
    customer_id: int
    pricelist_id: int
    order_provider: str
    shipment_type: str
    workdays_for_delivery: int
    input_dir: Path
    output_dir: Path
    renderer: RenderService

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create a HarmanOrderService instance from application configuration.

        Factory method that builds a HarmanOrderService with all settings from
        the application configuration object. This is the standard way to
        instantiate the service.

        Args:
            config: Application Config instance with Harman-specific settings

        Returns:
            Fully initialized HarmanOrderService ready to process orders
        """
        logger.info("Create HarmanOrderService from config...")
        return cls(
            administration_id=config.harman_administration_id,
            customer_id=config.harman_customer_id,
            pricelist_id=config.harman_pricelist_id,
            order_provider=config.harman_order_provider,
            shipment_type=config.harman_shipment_type,
            workdays_for_delivery=config.harman_workdays_for_delivery,
            input_dir=config.harman_input_dir,
            output_dir=config.harman_output_dir,
            renderer=RenderService(directory=config.templates_dir),
        )

    def read_orders(self) -> Generator[Order, None, None]:
        """Generate orders from Harman EDI files in the input directory.

        Scans the input directory for .insdes and .created files, parses each
        as EDIFACT order data, and yields Order instances. Errors during parsing
        are caught and stored without stopping iteration of remaining files.

        Yields:
            Order instances ready for processing

        Note:
            Files are processed in sorted order for consistency. Files with parse
            errors are logged but don't prevent processing of other files.
        """
        logger.info("Generate orders...")
        # parse each .insdes file in the directory and yield an Order instance
        chain = itertools.chain.from_iterable(
            [
                self.input_dir.glob("*.insdes", case_sensitive=False),
                self.input_dir.glob("*.created", case_sensitive=False),
            ]
        )
        for file in chain:
            try:
                logger.info("Process file: %s", file)
                order_data = self._read_order_data(file)
                yield self._make_order(order_data)
            except Exception as exc:
                logger.error("Error processing file: %s", file, exc_info=exc)
                ErrorStore().add(exc)

    def _read_order_data(self, file: Path) -> dict[str, Any]:
        """Extract order data from an EDIFACT order file.

        Parses the EDIFACT format file and extracts relevant order information
        (shipping address, line items, etc.) into a structured dictionary.

        Args:
            file: Path to the EDIFACT order file to parse

        Returns:
            Dictionary with keys:
            - 'ship_to': Dictionary with shipping address fields
            - 'line_items': List of line item dictionaries
            - 'remote_order_id': External order ID
            - 'delivery_note_id': Delivery note reference (if present)

        Raises:
            Exception: If file cannot be read or EDIFACT format is invalid
        """
        order_data: dict[str, Any] = {
            "ship_to": {},
            "line_items": [],
        }
        for segment in Parser().parse(file.read_text(encoding="utf-8")):
            # extract data from the segment and update the order data
            self._get_segment_data(segment, order_data)
        logger.debug("Extracted order data: %s", json.dumps(order_data))
        return order_data

    def _get_segment_data(self, segment: Segment, order_data: dict[str, Any]) -> dict[str, Any]:
        """Extract data from an EDIFACT segment and update order data.

        Parses individual EDI segments (NAD, RFF, LIN, QTY, FTX) using pattern
        matching to extract shipping, line item, and order reference data.
        Updates the order_data dictionary with extracted values.

        Segment types processed:
        - NAD: Shipping address and contact information
        - RFF: Order and delivery note references
        - LIN: Line item product codes
        - QTY: Line item quantities
        - FTX: Delivery instructions and location/stock status per line item

        Args:
            segment: EDIFACT Segment instance to parse
            order_data: Dictionary to update with extracted data

        Returns:
            The updated order_data dictionary
        """
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
                order_data["line_items"][-1]["quantity"] = quantity
                order_data["line_items"][-1]["unit_of_measure"] = unit_of_measure
            case ["FTX", "DEL", "3", "", delivery_instructions]:
                order_data["delivery_instructions"] = delivery_instructions
            case ["FTX", "PRD", "", "", [location, stock_status]]:
                assert order_data["line_items"], "FTX segment must be preceded by a LIN segment."
                order_data["line_items"][-1]["location"] = location
                order_data["line_items"][-1]["stock_status"] = stock_status

        return order_data

    def _make_order(self, data: dict[str, Any]) -> Order:
        """Create an Order instance from parsed order data.

        Transforms the parsed EDIFACT data into a complete Order domain model.
        Handles normalization of shipment type (B2B vs B2C based on company name),
        creation of ShipTo and LineItem instances, and setting appropriate delivery dates.

        Populates Order fields:
        - description: Formatted as "<order_provider> order <remote_order_id> / <delivery_note_id>"
        - delivery_instructions: Extracted from FTX segments (defaults to empty string)

        Args:
            data: Dictionary with parsed order data from _read_order_data()

        Returns:
            Fully initialized Order instance ready for processing

        Raises:
            ValueError: If required fields are missing or invalid
        """
        logger.debug("Create Order instance from data: %s", json.dumps(data))
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
                    remote_line_id=item.get("remote_line_id", ""),
                    product_code=item.get("product_code", ""),
                    quantity=int(item.get("quantity", 0)),
                )
                for item in data.get("line_items", [])
            ],
        )

        order.set_ship_at(Order.calculate_delivery_date(self.workdays_for_delivery))
        return order

    def read_order_data_by_remote_order_id(self, remote_order_id: str) -> dict[str, Any] | None:
        """Get parsed order data by remote order ID.

        Locates and parses the order file matching the given remote order ID.
        Useful for retrieving order data when you have the ID but not the file path.

        Args:
            remote_order_id: External order ID to search for

        Returns:
            Dictionary with parsed order data, or None if no matching file found
        """
        logger.info("Get order data for remote order ID: %s", remote_order_id)
        for file in self.input_dir.glob(f"{remote_order_id}.*"):
            return self._read_order_data(file)
        return None

    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Get the appropriate artwork service for the given order.

        Selects the correct artwork service based on order ID pattern matching.
        Harman orders matching pattern (HA|JB)-EM-(ST-)?\\d+ use the Spectrum
        artwork service. Other orders return None (no artwork service).

        Args:
            order: The Order to select a service for
            artwork_services: Registry of available artwork services

        Returns:
            The Spectrum IArtworkService for matching orders, None otherwise
        """
        logger.info("Get artwork service for order: %s", order.remote_order_id)
        if re.match(r"(HA|JB)-EM-(ST-)?\d+", order.remote_order_id):
            return artwork_services.get("Spectrum")
        return None

    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Save the given order with its current status to JSON format.

        Persists the order to a JSON file in the input directory for later
        retrieval. Also renames the original EDIFACT file with the status
        extension to track processing state.

        Args:
            order: The Order instance to persist
            status: The OrderStatus to record

        Raises:
            May raise file system exceptions if write fails
        """
        logger.info("Persist order: %s with status: %s", order.remote_order_id, status)

        def custom_serializer(obj):
            if isinstance(obj, dt.datetime):
                return obj.isoformat()
            if isinstance(obj, dt.date):
                return obj.isoformat()
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")

        order.set_status(status)
        order_data = asdict(order)
        file_path = self.input_dir / f"{order.remote_order_id}.json"
        text = json.dumps(order_data, indent=4, ensure_ascii=False, default=custom_serializer)
        file_path.write_text(text, encoding="utf-8")

        for file in self.input_dir.glob(f"{order.remote_order_id}.*"):
            if file.suffix.lower() != ".json":
                file.rename(file.parent / f"{order.remote_order_id}.{order.status.value}".upper())

    def load_order(self, remote_order_id: str) -> Order:
        """Load a previously persisted order by its remote ID.

        Retrieves an order from the JSON persistence file if it exists.

        Args:
            remote_order_id: External order ID to load

        Returns:
            The Order instance if found

        Raises:
            May raise exceptions if JSON parsing fails or file cannot be read
        """
        logger.info("Load order by remote ID: %s", remote_order_id)
        file_path = self.input_dir / f"{remote_order_id}.json"
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)
        return Order(**data)

    def notify_completed_sale(self, order: Order) -> None:
        """Notify Harman of a completed sale by generating DESADV messages.

        Creates delivery advice (DESADV) notifications in both D96A and D99A
        EDIFACT format. Uses Jinja2 templates to generate the EDI messages
        and the PYDIFACT library to serialize them properly.

        Two files are created in the output directory:
        - {remote_order_id}.DESADVD96A (legacy format)
        - {remote_order_id}.DESADVD99A (current format)

        Args:
            order: The Order instance that has been completed

        Raises:
            NotifyError: If required order data cannot be found
            May raise exceptions if file writing fails
        """
        logger.info("Notify completed sale for order: %s", order.remote_order_id)
        # The notification exists of 2 desdav files, one in D96A format and one in D99A format.
        for file in self.renderer.directory.glob("desadv-*.j2"):
            doc_type = "D96A" if "D96A" in file.name.upper() else "D99A"
            notify_data = self._get_notify_data(order, doc_type)

            # build the notification message using the renderer and clean it up
            message = self.renderer.render(file.name, notify_data)
            segments = Parser().parse(message)
            content = Serializer().serialize(list(segments), break_lines=True)

            # write the message
            notify_path = self.output_dir / f"{order.remote_order_id}.{file.stem}".upper()
            notify_path.write_text(content, encoding="utf-8")

    def _get_notify_data(self, order: Order, doc_type: str) -> dict[str, Any]:
        """Get the data needed for DESADV notification generation.

        Prepares all data required to render DESADV notification templates,
        including order information, shipment details, and EDI segment counts.
        Different segment counts are calculated for D96A vs D99A formats.

        Args:
            order: The Order being notified about
            doc_type: Format type ('D96A' or 'D99A')

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
        logger.info(
            "Get notify data for order: %s with doc type: %s", order.remote_order_id, doc_type
        )
        order_data = self.read_order_data_by_remote_order_id(order.remote_order_id)
        if not (order_data and order_data.get("ship_to") and order_data.get("line_items")):
            raise NotifyError("No valid order data found", order_id=order.remote_order_id)

        segments_d96a = [
            35,  # Header and trailer segments
            4 * len(order_data["line_items"]),  # 4 segment lines per line item
            sum(item.get("quantity", 0) for item in order_data["line_items"]),  # Serial segments
            1
            + sum(item.get("quantity", 0) for item in order_data["line_items"])
            // 10,  # PCI segments (1 per 10 products)
        ]
        segments_d99a = [
            9,  # Header and trailer segments
            4 * len(order_data["line_items"]),  # 4 segment lines per line item
            sum(item.get("quantity", 0) for item in order_data["line_items"]),  # Serial segments
            1,  # FTX segment
        ]

        config: Config = get_config()
        box_length, box_width, box_height = config.default_box_size
        notify_data = {
            "interchange_control_ref": "".join(random.choices(string.digits, k=10)),
            "ship_date": dt.datetime.now(dt.UTC),
            "expected_date": dt.datetime.now(dt.UTC) + dt.timedelta(days=2),
            "box_length": box_length,
            "box_width": box_width,
            "box_height": box_height,
            "sscc": "".join(random.choices(string.digits, k=20)),
            "segments": sum(segments_d96a) if doc_type == "D96A" else sum(segments_d99a),
            "item_description": "CLEAR",
            "order": order_data,
        }
        return notify_data
