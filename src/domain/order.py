"""Order class."""

import datetime as dt
import uuid
from dataclasses import dataclass, field
from enum import Enum

import src.domain.validators as validators
from src.domain.line_item import LineItem
from src.domain.ship_to import ShipTo


class OrderStatus(Enum):
    """Order status enumeration."""

    NEW = "new"
    CREATED = "created"
    ARTWORK = "artwork"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    SHIPPED = "shipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    """Order entity."""

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    sale_id: int = field(default=0, init=False)
    administration_id: int
    customer_id: int
    order_provider: str
    pricelist_id: int
    remote_order_id: str
    shipment_type: str
    status: OrderStatus = field(default=OrderStatus.NEW, init=False)
    ship_to: ShipTo
    line_items: list[LineItem] = field(default_factory=list)
    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(), init=False)
    ship_at: dt.date = field(
        default_factory=lambda: dt.date.today() + dt.timedelta(days=7), init=False
    )

    def __post_init__(self) -> None:
        """Validate the order data."""
        validators.validate_positive_int(self.administration_id, "Administration ID")
        validators.validate_positive_int(self.customer_id, "Customer ID")
        validators.validate_positive_int(self.pricelist_id, "Pricelist ID")

        validators.validate_non_empty_string(self.order_provider, "Order provider")
        validators.set_normalized_string(self, "order_provider", self.order_provider)

        validators.validate_non_empty_string(self.remote_order_id, "Remote order ID")
        validators.set_normalized_string(self, "remote_order_id", self.remote_order_id)

        validators.validate_non_empty_string(self.shipment_type, "Shipment type")
        validators.set_normalized_string(self, "shipment_type", self.shipment_type)

        validators.validate_instance(self.ship_to, ShipTo, "Ship to")

        # line_items has a specific error message that covers all cases
        if not (
            isinstance(self.line_items, list)
            and self.line_items
            and all(isinstance(item, LineItem) for item in self.line_items)
        ):
            raise ValueError("Line items must be a list of LineItem instances.")

    def set_sale_id(self, value: int) -> None:
        """Set the sale ID."""
        if not (isinstance(value, int) and value > 0):
            raise ValueError("value must be a positive integer.")
        object.__setattr__(self, "sale_id", value)

    def set_status(self, value: OrderStatus) -> None:
        """Set the order status."""
        validators.validate_instance(value, OrderStatus, "Status")
        object.__setattr__(self, "status", value)

    @staticmethod
    def calculate_delivery_date(workdays: int) -> dt.date:
        """Calculate the delivery date for the order."""
        validators.validate_non_negative_int(workdays, "Workdays for delivery")
        delivery_date = dt.date.today()
        while workdays > 0:
            delivery_date += dt.timedelta(days=1)
            if delivery_date.weekday() < 5:  # Monday to Friday are considered workdays
                workdays -= 1
        return delivery_date

    def set_ship_at(self, ship_at: dt.date) -> None:
        """Set the ship at date."""
        if not isinstance(ship_at, dt.date) or ship_at <= dt.date.today():
            raise ValueError("Ship at must be a date in the future.")
        object.__setattr__(self, "ship_at", ship_at)

    @property
    def description(self) -> str:
        """Get a description of the order."""
        return f"{self.order_provider} Order {self.remote_order_id}"
