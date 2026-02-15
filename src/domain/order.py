"""Order class."""

from dataclasses import dataclass, field
import datetime as dt
from enum import Enum

from src.domain.line_item import LineItem
from src.domain.ship_to import ShipTo


class OrderStatus(Enum):
    """Order status enumeration."""

    NEW = "new"
    CREATED = "created"
    ARTWORK = "artwork"
    COMPLETED = "completed"
    SHIPPED = "shipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    """Order entity."""

    id: int = field(default=0, init=False)
    administration_id: int
    customer_id: int
    order_provider: str
    pricelist_id: int
    remote_order_id: str
    shipment_type: str
    status: OrderStatus = field(default=OrderStatus.NEW, init=False)
    ship_to: ShipTo
    line_items: list[LineItem] = field(default_factory=list)
    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC), init=False)
    ship_at: dt.date = field(
        default_factory=lambda: dt.date.today() + dt.timedelta(days=7), init=False
    )

    def __post_init__(self):
        """Validate the order data."""

        if not (isinstance(self.administration_id, int) and self.administration_id > 0):
            raise ValueError("Administration ID must be a positive integer.")

        if not (isinstance(self.customer_id, int) and self.customer_id > 0):
            raise ValueError("Customer ID must be a positive integer.")

        if not (isinstance(self.order_provider, str) and self.order_provider.strip()):
            raise ValueError("Order provider must be a non-empty string.")
        object.__setattr__(self, "order_provider", self.order_provider.strip())

        if not (isinstance(self.pricelist_id, int) and self.pricelist_id > 0):
            raise ValueError("Pricelist ID must be a positive integer.")

        if not (isinstance(self.remote_order_id, str) and self.remote_order_id.strip()):
            raise ValueError("Remote order ID must be a non-empty string.")
        object.__setattr__(self, "remote_order_id", self.remote_order_id.strip())

        if not (isinstance(self.shipment_type, str) and self.shipment_type.strip()):
            raise ValueError("Shipment type must be a non-empty string.")
        object.__setattr__(self, "shipment_type", self.shipment_type.strip())

        if not isinstance(self.ship_to, ShipTo):
            raise ValueError("Ship to must be an instance of ShipTo.")

        if not (
            isinstance(self.line_items, list)
            and self.line_items
            and all(isinstance(item, LineItem) for item in self.line_items)
        ):
            raise ValueError("Line items must be a list of LineItem instances.")

    def set_id(self, value: int) -> None:
        """Set the order ID."""
        if not (isinstance(value, int) and value > 0):
            raise ValueError("ID must be a positive integer.")
        object.__setattr__(self, "id", value)

    def set_status(self, value: OrderStatus) -> None:
        """Set the order status."""
        if not isinstance(value, OrderStatus):
            raise ValueError("Status must be an instance of OrderStatus.")
        object.__setattr__(self, "status", value)

    @staticmethod
    def calculate_delivery_date(workdays: int) -> dt.date:
        """Calculate the delivery date for the order."""
        if workdays < 0:
            raise ValueError("Workdays for delivery must be a non-negative integer.")
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
