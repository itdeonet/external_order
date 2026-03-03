"""Domain model for customer orders.

This module defines the Order entity and OrderStatus enumeration. Orders represent
customer purchase requests with associated line items and shipping information.
Orders are immutable and validated at construction time, progressing through
well-defined lifecycle states from creation to completion.

Validation ensures:
- All numeric IDs are positive integers
- Provider, order ID, and shipment type are non-empty strings
- Ship-to address is a valid ShipTo instance
- At least one LineItem is present and valid
"""

import datetime as dt
import uuid
from dataclasses import dataclass, field
from enum import Enum

import src.domain.validators as validators
from src.domain.line_item import LineItem
from src.domain.ship_to import ShipTo


class OrderStatus(Enum):
    """Enumeration of order lifecycle states.

    Describes the progression of an order through the order management system.
    Each status represents a phase in the order processing workflow.

    Attributes:
        NEW: Order created but not yet submitted to the system
        CREATED: Order submitted and acknowledged by the system
        ARTWORK: Order awaiting artwork or design approval
        CONFIRMED: Order confirmed and ready for fulfillment
        COMPLETED: Order fulfilled and shipped
        SHIPPED: Order delivered to customer
        FAILED: Order processing failed or cancelled
    """

    NEW = "new"
    CREATED = "created"
    ARTWORK = "artwork"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    SHIPPED = "shipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    """Immutable order entity representing a customer purchase request.

    An order contains one or more line items, each specifying a product, quantity,
    and optional artwork. The order includes shipping destination details and
    progresses through defined lifecycle states from creation to completion.
    All fields are validated during post-initialization and are immutable
    after construction.

    This class enforces:
    - Immutability: All attributes are read-only after object creation
    - Validation: All fields must meet strict domain requirements
    - Lifecycle management: Orders progress through defined status states
    - Auto-generated fields: ID, sale_id (set later), status, timestamps
    - Default dates: Orders default to 7-day lead time

    Attributes:
        id: Unique auto-generated UUID for this order
        sale_id: Internal sale reference ID (set via set_sale_id, default 0)
        administration_id: Reference to the administration unit (must be positive)
        customer_id: Reference to the customer (must be positive)
        order_provider: Name of the order provider/source (non-empty string)
        pricelist_id: Reference to the pricing rules (must be positive)
        remote_order_id: External ID from source system (non-empty string)
        shipment_type: Type of shipment (e.g., 'Standard', non-empty string)
        description: Order description/summary (non-empty string, whitespace trimmed)
        delivery_instructions: Special delivery instructions (optional, default empty,
            whitespace trimmed)
        status: Current order lifecycle state (default: NEW)
        ship_to: ShipTo instance with delivery address details
        line_items: List of LineItem instances to order (must contain at least one)
        created_at: Timestamp when order was created (auto-generated)
        ship_at: Target shipping date (default: 7 days from creation)

    Example:
        >>> from src.domain import ShipTo, LineItem
        >>> ship_to = ShipTo(
        ...     remote_customer_id="CUST123",
        ...     contact_name="John Doe",
        ...     email="john@example.com",
        ...     phone="+1234567890",
        ...     street1="123 Main St",
        ...     city="Springfield",
        ...     state="IL",
        ...     postal_code="62701",
        ...     country_code="US",
        ... )
        >>> line_item = LineItem(remote_line_id="LI001", product_code="SKU123", quantity=50)
        >>> order = Order(
        ...     administration_id=1,
        ...     customer_id=123,
        ...     order_provider="Harman",
        ...     pricelist_id=1,
        ...     remote_order_id="ORDER123",
        ...     shipment_type="Standard",
        ...     description="Harman Order ORDER123",
        ...     delivery_instructions="Please deliver between 9-5",
        ...     ship_to=ship_to,
        ...     line_items=[line_item],
        ... )
        >>> order.set_sale_id(456)
        >>> order.set_status(OrderStatus.CONFIRMED)
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    sale_id: int = field(default=0, init=False)
    administration_id: int
    customer_id: int
    order_provider: str
    pricelist_id: int
    remote_order_id: str
    shipment_type: str
    description: str
    delivery_instructions: str = field(default="")
    status: OrderStatus = field(default=OrderStatus.NEW, init=False)
    ship_to: ShipTo
    line_items: list[LineItem] = field(default_factory=list)
    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(), init=False)
    ship_at: dt.date = field(
        default_factory=lambda: dt.date.today() + dt.timedelta(days=7), init=False
    )

    def __post_init__(self) -> None:
        """Validate and normalize all order fields after initialization.

        This method is called automatically by the dataclass decorator after
        the instance is created. It validates each field according to domain
        rules and normalizes string values. All validations must pass before
        the object is considered fully initialized.

        Validation steps performed:
        1. administration_id: positive integer (>0)
        2. customer_id: positive integer (>0)
        3. pricelist_id: positive integer (>0)
        4. order_provider: non-empty string, normalized (whitespace trimmed)
        5. remote_order_id: non-empty string, normalized (whitespace trimmed)
        6. shipment_type: non-empty string, normalized (whitespace trimmed)
        7. ship_to: ShipTo instance
        8. line_items: non-empty list of LineItem instances

        Raises:
            ValueError: If administration_id, customer_id, or pricelist_id is not positive
            ValueError: If order_provider, remote_order_id, or shipment_type is empty
            ValueError: If ship_to is not a ShipTo instance
            ValueError: If line_items is not a list of LineItem instances or is empty
        """
        validators.validate_positive_int(self.administration_id, "Administration ID")
        validators.validate_positive_int(self.customer_id, "Customer ID")
        validators.validate_positive_int(self.pricelist_id, "Pricelist ID")

        validators.validate_non_empty_string(self.order_provider, "Order provider")
        validators.set_normalized_string(self, "order_provider", self.order_provider)

        validators.validate_non_empty_string(self.remote_order_id, "Remote order ID")
        validators.set_normalized_string(self, "remote_order_id", self.remote_order_id)

        validators.validate_non_empty_string(self.shipment_type, "Shipment type")
        validators.set_normalized_string(self, "shipment_type", self.shipment_type)

        validators.validate_non_empty_string(self.description, "Description")
        validators.set_normalized_string(self, "description", self.description)

        validators.validate_instance(self.delivery_instructions, str, "Delivery instructions")
        validators.set_normalized_string(self, "delivery_instructions", self.delivery_instructions)

        validators.validate_instance(self.ship_to, ShipTo, "Ship to")

        # line_items has a specific error message that covers all cases
        if not (
            isinstance(self.line_items, list)
            and self.line_items
            and all(isinstance(item, LineItem) for item in self.line_items)
        ):
            raise ValueError("Line items must be a list of LineItem instances.")

    def set_sale_id(self, value: int) -> None:
        """Assign the internal sale reference ID to this order.

        This method allows setting the sales system ID after the order is
        created. The sale_id must be a positive integer. Despite the class
        being frozen, this method uses object.__setattr__ to modify the
        sale_id field, as permitted for specific domain operations.

        Args:
            value: Positive integer representing the sale reference ID.
                   Must be greater than 0.

        Raises:
            ValueError: If value is not a positive integer.

        Example:
            >>> order.set_sale_id(456)
        """
        if not (isinstance(value, int) and value > 0):
            raise ValueError("value must be a positive integer.")
        object.__setattr__(self, "sale_id", value)

    def set_status(self, value: OrderStatus) -> None:
        """Transition the order to a new lifecycle state.

        This method updates the order's processing status. The status must be
        a valid OrderStatus enumeration value. Despite the class being frozen,
        this method uses object.__setattr__ to modify the status field, as
        permitted for specific domain operations.

        Args:
            value: OrderStatus enumeration value representing the new state.
                   Must be a valid OrderStatus member.

        Raises:
            ValueError: If value is not an OrderStatus instance.

        Example:
            >>> order.set_status(OrderStatus.CONFIRMED)
            >>> order.set_status(OrderStatus.SHIPPED)
        """
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
