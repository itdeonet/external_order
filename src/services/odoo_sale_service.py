"""Odoo sales management service implementation.

This module provides the OdooSaleService, which manages the complete sales lifecycle
in Odoo for orders received from external providers. It implements the ISaleService protocol.

Key responsibilities:
- Creating and retrieving sales orders in Odoo from Order domain models
- Managing shipping contacts and addresses for deliveries
- Converting order line items to Odoo product format
- Confirming sales after validation and artwork processing
- Tracking shipments and retrieving product serial numbers
- Executing JSON-RPC calls to Odoo backend server
- Resolving references (products, carriers, countries, states) in Odoo

The service uses Odoo's JSON-RPC API to communicate with a configured Odoo instance
and validates all operations with proper error handling via SaleError exceptions.
"""

import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

import httpx

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.domain import Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooSaleService:
    """Service for managing sales in Odoo ERP system.

    This service creates and manages sales orders in Odoo based on Order domain
    models from external order providers. It handles the complete order-to-sale
    workflow including contact management, line item conversion, shipping tracking,
    and serial number management.

    All fields are configuration values for connecting to and authenticating with
    the Odoo JSON-RPC API.

    This class enforces:
    - Frozen: All attributes are read-only after creation
    - Authentication: OdooAuth instance with database, user, and password
    - HTTP client: httpx.Client configured with Odoo base URL
    - ID generation: Monotonic counter for JSON-RPC request IDs

    Attributes:
        auth: OdooAuth instance with database, user_id, and password credentials
        engine: httpx.Client configured with Odoo server base URL
        _id_counter: Auto-generated monotonic counter for RPC request IDs

    Example:
        >>> from src.app.odoo_auth import OdooAuth
        >>> import httpx
        >>> auth = OdooAuth(database="odoo_db", user_id=2, password="admin")
        >>> client = httpx.Client(base_url="http://odoo-server:8069")
        >>> service = OdooSaleService(auth=auth, engine=client)
        >>> sale_id = service.create_sale(order)
        >>> service.confirm_sale(order)
    """

    auth: OdooAuth
    engine: httpx.Client
    _id_counter: Iterator[int] = field(default_factory=lambda: iter(range(1, 1000000)), init=False)

    def __post_init__(self) -> None:
        """Validate authentication and HTTP client after initialization.

        Ensures that the OdooAuth credentials and httpx.Client are properly
        configured before the service is used. Raises ValueError if any
        required component is missing.

        Raises:
            ValueError: If auth is missing or not OdooAuth instance
            ValueError: If engine is missing or not httpx.Client instance
            ValueError: If engine base URL is not configured
        """
        if not (self.auth and isinstance(self.auth, OdooAuth)):
            raise ValueError("Odoo authentication information is missing or invalid")
        if not (self.engine and isinstance(self.engine, httpx.Client)):
            raise ValueError("Odoo engine is missing or invalid")
        if not (self.engine.base_url):
            raise ValueError("Odoo engine base URL is not set")

    def _get_sale_data(self, order: Order) -> dict[str, Any]:
        """Retrieve sale order data from Odoo by order reference.

        Searches Odoo for an existing sale.order record matching the order's
        remote ID or name. Searches within the correct company/administration unit.

        Args:
            order: The Order instance to look up in Odoo

        Returns:
            Dictionary with sale order data if found, empty dict {} if not found.
            Contains all sale.order fields when found.
        """
        logger.info("Get OdooSale for order: %s", order.remote_order_id)
        result = self._call(
            model="sale.order",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    "|",
                    ["x_remote_id", "=", order.remote_order_id],
                    ["name", "=", order.remote_order_id],
                ]
            ],
            query_options={"limit": 1},
        )

        if not (result and isinstance(result, list) and isinstance(result[0], dict)):
            return {}
        return result[0]

    def is_sale_created(self, order: Order) -> bool:
        """Check if a sale order has been created in Odoo for the given order.

        Determines whether Odoo already has a sale order matching this order's
        remote ID. Used to prevent duplicate sale creation.

        Args:
            order: The Order to check for

        Returns:
            True if a matching sale exists, False otherwise
        """
        logger.info("Is order %s created?", order.remote_order_id)
        result = bool(self._get_sale_data(order).get("id", 0))
        logger.info("Sale for order %s created: %s", order.remote_order_id, result)
        return result

    def _get_country_id(self, country_code: str) -> int:
        """Resolve ISO 3166-1 alpha-2 country code to Odoo res.country ID.

        Looks up the country ID in Odoo's country master data by the
        standardized 2-letter ISO country code.

        Args:
            country_code: ISO 3166-1 alpha-2 country code (case-insensitive)

        Returns:
            Integer country ID from Odoo

        Raises:
            SaleError: If country code is not found in Odoo
            TypeError: If returned ID is not an integer
        """
        logger.info("Get country ID for country code: %s", country_code)
        country_id = self._call_search_single(
            model="res.country",
            query_data=[["code", "=", country_code.strip().upper()[:2]]],
            error_message=f"Country code '{country_code}' not found",
        )
        logger.info("Found country ID %d for country code %s", country_id, country_code)
        if not isinstance(country_id, int):
            raise TypeError("country_id should be an integer")
        return country_id

    def _get_state_id(self, country_id: int, state: str) -> int:
        """Resolve region/state name to Odoo res.country.state ID.

        Looks up state/province ID in Odoo by name and country. Returns 0
        if state is empty or not found (optional field).

        Args:
            country_id: The Odoo country ID to search within
            state: State/province name (case-insensitive)

        Returns:
            Integer state ID from Odoo, or 0 if empty or not found

        Raises:
            TypeError: If returned ID is not an integer
        """
        logger.info("Get state ID for country_id=%s region=%s", country_id, state)
        if not (state := state.strip()):
            return 0

        state_id = self._call_search_single(
            model="res.country.state",
            query_data=[["country_id", "=", country_id], ["name", "ilike", state]],
            fields=["id"],
        )

        if state_id is None:
            logger.warning("State '%s' not found for country_id %d, returning 0", state, country_id)
            return 0

        logger.info("Found state ID %d for country_id=%s region=%s", state_id, country_id, state)
        if not isinstance(state_id, int):
            raise TypeError("state_id should be an integer")
        return state_id

    def _get_contact_data_from_order(self, order: Order) -> dict[str, Any]:
        """Build Odoo contact/partner data from Order shipping information.

        Transforms the Order's ship_to details into Odoo res.partner fields.
        Resolves country and state references and handles optional fields.

        Args:
            order: The Order to extract shipping data from

        Returns:
            Dictionary with Odoo res.partner fields ready for create/write
        """
        logger.info("Build contact data from order: %s", order.remote_order_id)
        ship_to = order.ship_to
        country_id = self._get_country_id(ship_to.country_code)
        state_id = (
            self._get_state_id(country_id, ship_to.state)
            if ship_to.state and ship_to.state.strip()
            else 0
        )
        return {
            "company_id": int(order.administration_id),
            "parent_id": int(order.customer_id),
            "ref": ship_to.remote_customer_id,
            "name": ship_to.contact_name,
            "company_name": ship_to.company_name or None,
            "type": "other",
            "is_company": True,
            "street": ship_to.street1,
            "street2": ship_to.street2 or None,
            "city": ship_to.city,
            "state_id": state_id or None,
            "zip": ship_to.postal_code,
            "country_id": country_id,
            "phone": ship_to.phone,
            "email": ship_to.email,
            "x_remote_source": order.order_provider,
        }

    def _create_contact(self, order: Order) -> int:
        """Create or retrieve shipping contact for the given order.

        Checks if a matching contact already exists in Odoo, returning its ID
        if found. Otherwise creates a new contact and returns the new ID.

        Args:
            order: The Order for which to create/retrieve contact

        Returns:
            Integer ID of the contact (res.partner) in Odoo

        Raises:
            ValueError: If contact data extraction fails
            SaleError: If contact creation fails
        """
        logger.info("Create contact for order: %s", order.remote_order_id)

        # build contact data from the order's ship_to information
        contact_data = self._get_contact_data_from_order(order)

        # check if a contact with the same fields already exists
        result = self._call(
            model="res.partner",
            method="search_read",
            query_data=[[[key, value] for key, value in contact_data.items()]],
            query_options={"fields": ["id"], "limit": 1},
        )

        if result and isinstance(result, list) and "id" in result[0]:
            contact_id = int(result[0]["id"])
            logger.info("Contact already exists with ID %d", contact_id)
            return contact_id

        # create a new contact if it doesn't exist
        contact_id = self._call(model="res.partner", method="create", query_data=[contact_data])
        if not (contact_id and isinstance(contact_id, int)):
            raise SaleError(f"Failed to create contact for order {order.remote_order_id}")

        logger.info("Created contact with ID %d", contact_id)
        return contact_id

    def _convert_order_lines(self, order: Order) -> list[dict[str, Any]]:
        """Convert Order line items to Odoo sale.order.line format.

        Transforms each LineItem into an Odoo order line by resolving product
        codes to Odoo product IDs and preparing necessary field values.

        Args:
            order: The Order whose line items to convert

        Returns:
            List of dictionaries in Odoo sale.order.line create format

        Raises:
            SaleError: If product lookup fails or validation fails
        """
        logger.info("Convert order lines for order: %s", order.remote_order_id)
        order_lines = []

        for line_item in order.line_items:
            # resolve line item product code to product ID and name in Odoo
            product = self._call_search_single(
                model="product.product",
                query_data=[["default_code", "=", line_item.product_code]],
                fields=["id", "name"],
                error_message=f"Product {line_item.product_code} not found",
            )

            if not isinstance(product, dict) or "id" not in product or "name" not in product:
                raise SaleError(
                    f"Product search for {line_item.product_code} failed", order.remote_order_id
                )
            order_lines.append(
                {
                    "product_id": product["id"],
                    "name": product["name"],
                    "product_uom_qty": line_item.quantity,
                }
            )

        logger.info("Converted order lines: %s", json.dumps(order_lines))
        return order_lines

    def _get_carrier_id(self, order: Order) -> int:
        """Resolve shipment type to Odoo delivery.carrier ID.

        Looks up the delivery carrier/shipping method in Odoo by matching
        the order's shipment type name.

        Args:
            order: The Order specifying the shipment type

        Returns:
            Integer carrier ID from Odoo

        Raises:
            ValueError: If shipment type is empty
            SaleError: If carrier is not found in Odoo
            TypeError: If returned ID is not an integer
        """
        carrier_name = order.shipment_type
        if not carrier_name.strip():
            raise ValueError("Shipment type is required in order")

        logger.info("Get carrier ID for name: %s", carrier_name)
        carrier_id = self._call_search_single(
            model="delivery.carrier",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    ["name", "=ilike", carrier_name],
                ]
            ],
            fields=["id"],
            error_message=f"Carrier '{carrier_name}' not found in Odoo",
        )

        logger.info("Found carrier ID %d for name: %s", carrier_id, carrier_name)
        if not isinstance(carrier_id, int):
            raise TypeError("carrier_id should be an integer")
        return carrier_id

    def create_sale(self, order: Order) -> int:
        """Create a sale order in Odoo from the given Order.

        Creates a new sale.order in Odoo with all details from the Order,
        including shipping contact, line items, and carrier. Returns the Odoo
        sale ID. If sale already exists, returns existing ID without duplication.

        Args:
            order: The Order to create a sale from

        Returns:
            Integer sale order ID (sale.order) in Odoo

        Raises:
            SaleError: If contact creation fails or sale creation fails
        """
        if sale_data := self._get_sale_data(order):
            logger.info(
                "Sale already exists for order %s from with ID %s",
                order.remote_order_id,
                sale_data["id"],
            )
            return sale_data["id"]

        logger.info("Create sale for order: %s", order.remote_order_id)
        contact_id = self._create_contact(order)
        sale_id = self._call(
            model="sale.order",
            method="create",
            query_data=[
                {
                    "partner_id": order.customer_id,
                    "partner_shipping_id": contact_id,
                    "company_id": order.administration_id,
                    "client_order_ref": order.description,
                    "pricelist_id": order.pricelist_id,
                    "order_line": self._convert_order_lines(order),
                    "state": "draft",
                    "commitment_date": order.ship_at.strftime("%Y-%m-%d"),
                    "carrier_id": self._get_carrier_id(order),
                    "x_remote_id": order.remote_order_id,
                    "x_remote_source": order.order_provider,
                }
            ],
        )

        if not isinstance(sale_id, int):
            raise SaleError("Failed to create sale", order.remote_order_id)

        logger.info("Created sale with ID %d for order %s", sale_id, order.remote_order_id)
        return sale_id

    def confirm_sale(self, order: Order) -> None:
        """Confirm sale order in Odoo (transition from draft to confirmed).

        Calls the sale.order action_confirm method to move the sale from
        draft state to confirmed state, triggering any configured workflows.

        Args:
            order: The Order whose sale should be confirmed

        Raises:
            SaleError: If sale does not exist or confirmation fails
        """
        sale_data = self._get_sale_data(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError("Cannot confirm non-existent sale", order.remote_order_id)

        sale_id = sale_data["id"]
        logger.info("Confirm sale with id: %s for order: %s", sale_id, order.remote_order_id)
        result = self._call(
            model="sale.order",
            method="action_confirm",
            query_data=[[sale_id]],
        )

        if not bool(result):
            raise SaleError("Failed to confirm sale", order.remote_order_id)

        logger.info("Sale with id %d confirmed successfully", sale_id)

    def has_expected_order_lines(self, order: Order) -> bool:
        """Verify that Odoo sale has expected line items and quantities.

        Compares the Order's line items against the sale order's lines in Odoo
        to ensure quantities match. Allows Odoo sale to have additional lines
        (for B2B manually created orders) as long as all order lines are present.

        Args:
            order: The Order with expected line items

        Returns:
            True if all order lines are in the sale, False if mismatch

        Raises:
            SaleError: If sale does not exist
        """
        logger.info(
            "Check if sale for order %s from provider %s has expected order lines in Odoo",
            order.remote_order_id,
            order.order_provider,
        )
        sale_data = self._get_sale_data(order)
        if not sale_data or "id" not in sale_data or sale_data["id"] == 0:
            raise SaleError("Cannot check order lines for non-existent sale", order.remote_order_id)

        odoo_lines = {
            (line["product_id"][0], line["product_uom_qty"])
            for line in self._call(
                model="sale.order.line",
                method="read",
                query_data=sale_data.get("order_line", []),
                query_options={"fields": ["product_id", "product_uom_qty"]},
            )
        }

        order_lines = {
            (li["product_id"], li["product_uom_qty"]) for li in self._convert_order_lines(order)
        }

        # B2B sales are manually created in Odoo and may have more lines than the order confirmation
        # So we check that all order lines are in the sale, but allow the sale to have extra lines.
        result = odoo_lines == order_lines or order_lines.issubset(odoo_lines)
        logger.info(
            "Order lines for order %s match expected lines: %s", order.remote_order_id, result
        )
        return result

    def update_contact(self, order: Order) -> None:
        """Update shipping contact information in Odoo.

        Retrieves the current shipping contact for the sale and updates it
        with fresh data from the Order.

        Args:
            order: The Order with updated shipping information

        Raises:
            SaleError: If sale does not exist, has no contact, or update fails
        """
        logger.info("Update contact information for order %s", order.remote_order_id)
        sale_data = self._get_sale_data(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError("Cannot update contact for non-existent sale", order.remote_order_id)

        contact_id: int = sale_data.get("partner_shipping_id", [0, ""])[0]
        if not contact_id:
            raise SaleError("Sale has no shipping contact to update", order.remote_order_id)

        contact_data = self._get_contact_data_from_order(order)
        result = self._call(
            model="res.partner",
            method="write",
            query_data=[[contact_id], contact_data],
        )
        if not bool(result):
            raise SaleError(f"Failed to update contact {contact_id}", order.remote_order_id)

        logger.info("Contact ID %d updated (order %s)", contact_id, order.remote_order_id)

    def get_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Get list of completed sales for a provider that need shipping notification.

        Retrieves sales that are fully delivered and in confirmed state, but have not
        yet had their shipping notification (DESADV) created.

        Args:
            order_provider: Name of the order provider to filter by
                           (e.g., 'Harman')

        Returns:
            List of tuples (sale_id: int, remote_order_id: str) for completed sales
        """
        logger.info("Get completed sales for order provider: %s", order_provider)
        result = self._call(
            model="sale.order",
            method="search_read",
            query_data=[
                [
                    ["delivery_status", "=", "full"],
                    ["state", "=", "sale"],
                    ["x_remote_source", "=", order_provider],
                    ["x_remote_desadv_created", "=", False],
                ]
            ],
            query_options={"fields": ["id", "x_remote_id"]},
        )

        if not (
            result
            and isinstance(result, list)
            and all(
                isinstance(item, dict) and "id" in item and "x_remote_id" in item for item in result
            )
        ):
            logger.info("No completed sales found for order provider %s", order_provider)
            return []

        logger.info(
            "Found %d completed sales for order provider %s: %s",
            len(result),
            order_provider,
            json.dumps(result),
        )
        return [(item["id"], item["x_remote_id"]) for item in result]

    def get_shipping_info(self, order: Order) -> list[dict[str, Any]]:
        """Get shipping/delivery information from Odoo for the given order.

        Retrieves stock.picking (shipment) records for completed deliveries,
        extracting carrier, tracking, weight, and delivery address information.

        Args:
            order: The Order to get shipping info for

        Returns:
            List of dictionaries with shipping details:
            - 'carrier': Carrier/shipping method name
            - 'carrier_tracking_ref': Tracking number
            - 'carrier_tracking_url': Tracking URL
            - 'ship_to_name': Delivery address contact name
            - 'weight': Shipment weight

        Raises:
            SaleError: If no shipping information found
        """
        logger.info("Get shipping information for order: %s", order.remote_order_id)
        sale_data = self._get_sale_data(order)
        result = self._call(
            model="stock.picking",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", sale_data["company_id"]],
                    ["picking_type_code", "=", "outgoing"],
                    ["sale_id", "=", sale_data.get("id", 0)],
                    ["state", "=", "done"],
                ]
            ],
            query_options={
                "fields": [
                    "carrier_id",
                    "carrier_tracking_ref",
                    "carrier_tracking_url",
                    "partner_id",
                    "weight",
                ]
            },
        )

        if not (
            result
            and isinstance(result, list)
            and all(
                isinstance(item, dict)
                and "carrier_id" in item
                and "carrier_tracking_ref" in item
                and "carrier_tracking_url" in item
                and "partner_id" in item
                and "weight" in item
                for item in result
            )
        ):
            raise SaleError("No shipping information found", order.remote_order_id)

        shipping_info = [
            {
                "carrier": item["carrier_id"][1],
                "carrier_tracking_ref": item["carrier_tracking_ref"],
                "carrier_tracking_url": item["carrier_tracking_url"],
                "ship_to_name": item["partner_id"][1],
                "weight": item["weight"],
            }
            for item in result
        ]
        logger.info(
            "Found shipping information for order %s: %s",
            order.remote_order_id,
            json.dumps(shipping_info),
        )
        return shipping_info

    def get_serials_by_line_item(self, order: Order) -> dict[str, list[str]]:
        """Get product serial numbers from Odoo grouped by order line item.

        Retrieves scanned serial numbers for products in the sale and groups
        them by the original order line items. Assigns serials in quantity order.

        Args:
            order: The Order to get serial numbers for

        Returns:
            Dictionary mapping line_item remote IDs to lists of serial numbers:
            {line_item_id: [serial1, serial2, ...], ...}
            Returns empty lists for line items with no serials.
        """
        logger.info("Get serial numbers for order: %s", order.remote_order_id)
        sale_data = self._get_sale_data(order)
        result = self._call(
            model="deonet.sale.scanned.serial",
            method="search_read",
            query_data=[
                [
                    ["order_id", "=", sale_data.get("id", 0)],
                ]
            ],
            query_options={"fields": ["product_id", "serial"]},
        )

        if not (
            result
            and isinstance(result, list)
            and all(
                isinstance(item, dict) and "product_id" in item and "serial" in item
                for item in result
            )
        ):
            # If there are no serials found, return an empty list for each line item
            return {li.remote_line_id: [] for li in order.line_items}

        # Group serials by product code extracted from product name
        # e.g. {code1: [serial1, serial2], code2: [serial3]}
        serials_by_product = defaultdict(list)
        for item in result:
            # item["product_id"] is a tuple of (id: int, name: str)
            # extract product code from name, which is in format "[CODE] Product Name"
            product_name = item["product_id"][1].split()[0][1:-1]
            serials_by_product[product_name].append(item["serial"])

        # Group serials by line item based on product code and quantity
        # e.g. {line_item_id1: [serial1, serial2], line_item_id2: [serial3]}
        serials_by_line_item = defaultdict(list)
        for li in order.line_items:
            # assign serials to line items based on product code and quantity
            serials_by_line_item[li.remote_line_id] = serials_by_product.get(li.product_code, [])[
                : li.quantity
            ]
            # remove assigned serials from the pool
            serials_by_product[li.product_code] = serials_by_product.get(li.product_code, [])[
                li.quantity :
            ]

        logger.info(
            "Found serial numbers for order %s: %s",
            order.remote_order_id,
            json.dumps(serials_by_line_item),
        )
        return serials_by_line_item

    def _call(
        self,
        model: str,
        method: str,
        query_data: list[Any] | None = None,
        query_options: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a JSON-RPC call to the Odoo server.

        Makes an authenticated JSON-RPC 2.0 call to the Odoo server using the
        configured httpx.Client. Automatically includes authentication credentials
        from OdooAuth. Handles RPC errors and raises SaleError on failures.

        Args:
            model: Odoo model name (e.g., 'sale.order', 'res.partner')
            method: Odoo method to call (e.g., 'create', 'write', 'search_read')
            query_data: Positional arguments for the RPC call (default: [])
            query_options: Keyword arguments/options for the call (default: {})

        Returns:
            The 'result' field from the JSON-RPC response

        Raises:
            SaleError: If JSON-RPC response contains an error
            httpx.HTTPError: If HTTP request fails
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.auth.database,
                    self.auth.user_id,
                    self.auth.password,
                    model,
                    method,
                    query_data or [],
                    query_options or {},
                ],
            },
            "id": next(self._id_counter),
        }

        logger.debug("Making JSON_RPC call with payload: %s", json.dumps(payload))
        response = self.engine.post("/jsonrpc", json=payload)
        response.raise_for_status()
        data = response.json()

        if error := data.get("error"):
            message = f"Odoo JSON-RPC error: {error.get('message')}"
            logger.warning(
                "%s, model=%s, method=%s, data=%s",
                message,
                model,
                method,
                error.get("data"),
            )
            raise SaleError(message)
        return data.get("result")

    def _call_search_single(
        self,
        model: str,
        query_data: list,
        fields: list[str] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any] | int | None:
        """Generic method for searching a single record by criteria.

        Wraps _call() with search_read for a single record lookup.

        Args:
            model: The Odoo model to search.
            query_data: The search criteria (domain filter).
            fields: Optional list of fields to return. Defaults to ["id"].
            error_message: Optional error message to raise if record not found.
                          If None, returns None instead of raising.

        Returns:
            The full record dict if multiple fields requested, the id if only id requested,
            or None if not found and no error_message provided.

        Raises:
            SaleError: If record not found and error_message is provided.
        """
        fields = fields or ["id"]
        result = self._call(
            model=model,
            method="search_read",
            query_data=[query_data],
            query_options={"fields": fields, "limit": 1},
        )

        if not (result and isinstance(result, list) and result[0]):
            if error_message:
                raise SaleError(error_message)
            return None

        record = result[0]
        # Validate that all requested fields are present in the record
        if not all(field in record for field in fields):
            if error_message:
                raise SaleError(error_message)
            return None

        # If only id field requested, return just the id as int
        if fields == ["id"]:
            return int(record["id"])
        # Otherwise return the full record dict
        return record
