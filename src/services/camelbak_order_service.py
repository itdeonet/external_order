"""Spectrum-specific order processing service.

Provides `SpectrumOrderService` for parsing Spectrum API orders, creating
`Order` models, persisting them, and generating completion notifications.
"""

import datetime as dt
import json
from collections.abc import Generator
from dataclasses import InitVar, asdict, dataclass, field
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Any

import requests

from src.app.errors import get_error_store
from src.config import get_config
from src.domain import (
    Artwork,
    IArtworkService,
    IRegistry,
    ISaleService,
    LineItem,
    Order,
    OrderStatus,
    ShipTo,
)

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class CamelbakOrderService:
    """Service to parse Spectrum API for Camelbak orders and manage their lifecycle.

    Configuration-driven; integrates with `RenderService` and `ErrorStore`.
    """

    session: requests.Session
    api_key: InitVar[str] = field(repr=False)
    base_url: str = field(default_factory=lambda: get_config().spectrum_base_url)
    artwork_provider_name: str = field(
        default_factory=lambda: get_config().camelbak_artwork_provider_name
    )
    administration_id: int = field(default_factory=lambda: get_config().camelbak_administration_id)
    customer_id: int = field(default_factory=lambda: get_config().camelbak_customer_id)
    pricelist_id: int = field(default_factory=lambda: get_config().camelbak_pricelist_id)
    order_provider: str = field(default_factory=lambda: get_config().camelbak_order_provider)
    shipment_type: str = field(default_factory=lambda: get_config().camelbak_shipment_type)
    workdays_for_delivery: int = field(
        default_factory=lambda: get_config().camelbak_workdays_for_delivery
    )
    input_dir: Path = field(default_factory=lambda: Path(get_config().camelbak_input_dir))

    def __post_init__(self, api_key: str) -> None:
        """post init to ensure the object is valid."""
        self.session.headers.update({"SPECTRUM_API_TOKEN": api_key})

    def read_orders(self) -> Generator[Order, None, None]:
        """Search the API for new orders and yield Order instances.

        Yields:
            Order: Parsed order from each input file.

        Note:
            Parsing errors are recorded in ErrorStore and do not stop iteration.
        """
        logger.info("Generate orders...")
        # search the API and yield an Order instance
        endpoint = "/api/orders/search/"
        json_data = {
            "lastModificationStartDate": dt.date.today().isoformat(),
            "workflowStatuses": ["not-started"],
        }
        response = self.session.post(f"{self.base_url.rstrip('/')}{endpoint}", json=json_data)
        response.raise_for_status()
        data: list[dict[str, Any]] = response.json()
        for order_data in data:
            try:
                yield self._make_order(order_data)
            except Exception as exc:
                logger.error("Failed to process order: %s", order_data, exc_info=exc)
                get_error_store().add(exc)

    def _make_order(self, data: dict[str, Any]) -> Order:
        """Create Order domain model from API data.

        Args:
            data: Structured order data from API.

        Returns:
            Order instance with ShipTo and LineItems populated from data.
        """
        logger.info("Create Order instance from order_data")
        ship_to_data: dict[str, Any] = data.get("shippingAddress", {})
        order = Order(
            administration_id=self.administration_id,
            customer_id=self.customer_id,
            order_provider=self.order_provider,
            pricelist_id=self.pricelist_id,
            remote_order_id=data.get("purchaseOrderNumber", ""),
            shipment_type=self.shipment_type,
            description=(f"{self.order_provider} order {data.get('purchaseOrderNumber', '')}"),
            delivery_instructions="",
            ship_to=ShipTo(
                remote_customer_id=data.get("userId", ""),
                company_name="",
                contact_name=f"{ship_to_data.get('firstName', '')} {ship_to_data.get('lastName', '')}",
                email=data.get("emailAddress", ""),
                phone=data.get("phoneNumber", ""),
                street1=ship_to_data.get("address1", ""),
                street2=ship_to_data.get("address2", ""),
                city=ship_to_data.get("city", ""),
                state=ship_to_data.get("state", "") or ship_to_data.get("province", ""),
                postal_code=ship_to_data.get("postalCode", ""),
                country_code=ship_to_data.get("country", ""),
            ),
            line_items=[
                LineItem(
                    line_id=item.get("recipeSetId", ""),
                    product_code=sku_qty.get("sku", ""),
                    quantity=int(sku_qty.get("quantity", 0)),
                )
                for item in data.get("lineItems", [])
                for sku_qty in item.get("skuQuantities", [])
            ],
        )

        order.set_ship_at(Order.calculate_delivery_date(self.workdays_for_delivery))
        return order

    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Return the matching artwork service for `order`, or `None` if none."""
        logger.info("Get artwork service for order: %s", order.remote_order_id)
        return artwork_services.get(self.artwork_provider_name)

    def should_update_sale(self, order: Order) -> bool:
        """Determine if an existing sale should be updated based on remote_order_id."""
        logger.info("Check if sale should be updated for order: %s", order.remote_order_id)
        return False  # Spectrum orders are immutable after creation, so we never update sales

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

        # update the API with the new workflow status
        endpoint = "/api/order/status/"
        json_data = {
            "purchaseOrderNumber": order.remote_order_id,
            "lineItems": [
                {"recipeSetReadableId": li.line_id, "workflowStatus": "in-progress"}
                for li in order.line_items
            ],
        }
        response = self.session.put(f"{self.base_url.rstrip('/')}{endpoint}", json=json_data)
        response.raise_for_status()

    def load_order(self, remote_order_id: str) -> Order:
        """Load and return an `Order` previously persisted as JSON."""
        logger.info("Load order by remote ID: %s", remote_order_id)
        file_path = self.input_dir / f"{remote_order_id}.json"
        text = file_path.read_text(encoding="utf-8")
        data = json.loads(text)

        # pop all non init fields and prepare the data for Order initialization
        sale_id = data.pop("sale_id", 0)
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
        order.set_sale_id(sale_id)
        order.set_status(OrderStatus(status))
        order.set_created_at(created_at)
        order.set_ship_at(ship_at)
        return order

    def notify_completed_sale(self, order: Order, notify_data: dict[str, Any]) -> None:
        """Notify Camelbak of a completed sale by updating the order data in the API.

        Args:
            order: The Order instance that has been completed
            notify_data: The data used to generate the notification

        Raises:
            NotifyError: If required order data cannot be found
            May raise exceptions if file writing fails
        """
        logger.info("Notify completed sale for order: %s", order.remote_order_id)
        endpoint = "/api/order/ship-notification/"
        json_data = {
            "purchaseOrderNumber": order.remote_order_id,
            "lineItems": [
                {
                    "recipeSetReadableId": li.line_id,
                    "shipmentTracking": notify_data.get("carrier_tracking_ref", ""),
                    "serialNumbers": [],
                }
                for li in order.line_items
            ],
        }
        response = self.session.post(f"{self.base_url.rstrip('/')}{endpoint}", json=json_data)
        response.raise_for_status()

    def get_notify_data(self, order: Order, sale_service: ISaleService) -> dict[str, Any]:
        """Get the data needed for notification.

        Args:
            order: The Order being notified about
            sale_service: The service used to interact with sales data

        Returns:
            Dictionary with notification data.

        Raises:
            NotifyError: If required order data cannot be retrieved
        """
        logger.info("Get notify data for order: %s", order.remote_order_id)

        # get shipping from the sale service to include in the notification
        shipping_info: dict[str, Any] = sale_service.search_shipping_info(order)[0]
        carrier_tracking_ref = shipping_info["carrier_tracking_ref"].split(", ")

        return {"carrier_tracking_ref": carrier_tracking_ref}
