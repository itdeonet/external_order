"""Odoo sales service: create, confirm and query sales via JSON-RPC.

Utilities for mapping domain `Order` objects to Odoo `sale.order` records.
"""

import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

import requests

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.config import get_config
from src.domain import Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooSaleService:
    """Manage sales in Odoo: map `Order` to `sale.order` and call RPC methods."""

    session: requests.Session
    auth: OdooAuth = field(default_factory=lambda: OdooAuth())
    base_url: str = field(default_factory=lambda: get_config().odoo_base_url)
    _id_counter: Iterator[int] = field(default_factory=lambda: iter(range(1, 1000000)), init=False)

    def __post_init__(self) -> None:
        """Validate `auth` and `engine` after creation, raise `ValueError` if invalid."""
        if not (self.auth and isinstance(self.auth, OdooAuth)):
            raise ValueError("Odoo authentication information is missing or invalid")
        if not (self.session and isinstance(self.session, requests.Session)):
            raise ValueError("Odoo session is missing or invalid")
        if not (self.base_url):
            raise ValueError("Odoo base URL is not set")
        self.session.verify = get_config().ssl_verify

    def _get_sale_data(self, order: Order) -> dict[str, Any]:
        """Query Odoo for sale order matching order's remote_order_id.

        Args:
            order: Order to search for.

        Returns:
            Sale order record dict if found, else empty dict.
        """
        logger.info("Get OdooSale for order: %s", order.remote_order_id)
        result = self._call(
            model="sale.order",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    ["x_remote_order_id", "=", order.remote_order_id],
                ]
            ],
            query_options={"limit": 1},
        )

        if not (result and isinstance(result, list) and isinstance(result[0], dict)):
            return {}
        return result[0]

    def is_sale_created(self, order: Order) -> bool:
        """Return True if a corresponding sale exists in Odoo for `order`.

        Updates `order.sale_id` if a sale is found. Returns False if no sale exists.

        Args:
            order: Order to check.

        Returns:
            True if sale exists, False otherwise.
        """
        logger.info("Is order %s created?", order.remote_order_id)
        if sale_id := int(self._get_sale_data(order).get("id", 0)):
            order.set_sale_id(sale_id)
        logger.info("Sale for order %s created: %s", order.remote_order_id, sale_id)
        return sale_id > 0

    def _get_country_id(self, country_code: str) -> int:
        """Lookup and return Odoo country ID by ISO country code.

        Args:
            country_code: ISO 2-letter country code.

        Returns:
            Odoo country record ID.

        Raises:
            SaleError: If country code not found in Odoo.
        """
        logger.info("Get country ID for country code: %s", country_code)
        result = self._call(
            model="res.country",
            method="search_read",
            query_data=[[["code", "=", country_code.strip().upper()[:2]]]],
            query_options={"fields": ["id"], "limit": 1},
        )

        if not (
            result
            and isinstance(result, list)
            and isinstance(result[0], dict)
            and (country_id := result[0].get("id", None))
            and isinstance(country_id, int)
            and country_id > 0
        ):
            raise SaleError(f"Country code '{country_code}' not found in Odoo")

        logger.info("Found country ID %d for country code %s", country_id, country_code)
        return country_id

    def _get_state_id(self, country_id: int, state: str) -> int:
        """Lookup and return Odoo state ID for a given country and state name.

        Args:
            country_id: Odoo country record ID.
            state: State name to search for (case-insensitive).

        Returns:
            Odoo state record ID, or 0 if not found.
        """
        logger.info("Get state ID for country_id=%s region=%s", country_id, state)
        if not (state := state.strip()):
            return 0

        result = self._call(
            model="res.country.state",
            method="search_read",
            query_data=[[["country_id", "=", country_id], ["name", "ilike", state]]],
            query_options={"fields": ["id"], "limit": 1},
        )

        if not (
            result
            and isinstance(result, list)
            and isinstance(result[0], dict)
            and (state_id := result[0].get("id", None))
            and isinstance(state_id, int)
        ):
            logger.warning("State '%s' not found for country_id %d, returning 0", state, country_id)
            return 0

        logger.info("Found state ID %d for country_id=%s region=%s", state_id, country_id, state)
        return state_id

    def _get_contact_data_from_order(self, order: Order) -> dict[str, Any]:
        """Map order shipping info to Odoo partner (contact) record data.

        Args:
            order: Order with ship_to and administration info.

        Returns:
            Dict of partner fields ready for Odoo create/write.
        """
        logger.info("Build contact data from order: %s", order.remote_order_id)
        ship_to = order.ship_to
        country_id = self._get_country_id(ship_to.country_code)
        state_id = (
            self._get_state_id(country_id, ship_to.state)
            if ship_to.state and ship_to.state.strip()
            else 0
        )
        # Odoo's "company_id" field is reserved for the Odoo company,
        # so we map the customer's company name to "deonet_other_company"
        return {
            "company_id": int(order.administration_id),
            "parent_id": int(order.customer_id),
            "ref": ship_to.remote_customer_id,
            "name": ship_to.contact_name,
            "deonet_other_company": ship_to.company_name or None,
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
            "x_remote_order_provider": order.order_provider,
            "active": False,  # archived, not loaded in client portal
            "portal_visible": False,
        }

    def _create_contact(self, order: Order) -> int:
        """Create or return existing Odoo partner (contact) for order ship_to location.

        Args:
            order: Order with shipping and contact info.

        Returns:
            Odoo partner record ID.

        Raises:
            SaleError: If contact creation fails.
        """
        logger.info("Create contact for order: %s", order.remote_order_id)

        # build contact data from the order's ship_to information
        contact_data = self._get_contact_data_from_order(order)

        # check if a contact with the same fields already exists
        result = self._call(
            model="res.partner",
            method="search_read",
            query_data=[[[key, "=", value] for key, value in contact_data.items()]],
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
        """Convert order line items to Odoo sale order line dicts.

        Args:
            order: Order with line_items to convert.

        Returns:
            List of dicts ready for Odoo order_line create.

        Raises:
            SaleError: If product lookup or mapping fails.
        """
        logger.info("Convert order lines for order: %s", order.remote_order_id)
        order_lines = []

        for line_item in order.line_items:
            # resolve line item product code to product ID and name in Odoo
            result = self._call(
                model="product.product",
                method="search_read",
                query_data=[[["default_code", "=", line_item.product_code]]],
                query_options={"fields": ["id", "name"], "limit": 1},
            )

            if not (
                result
                and isinstance(result, list)
                and isinstance(result[0], dict)
                and (product_id := result[0].get("id", None))
                and isinstance(product_id, int)
                and product_id > 0
                and (product_name := result[0].get("name", None))
                and isinstance(product_name, str)
                and product_name.strip()
            ):
                raise SaleError(
                    f"Product search for {line_item.product_code} failed", order.remote_order_id
                )

            order_lines.append(
                {
                    "product_id": product_id,
                    "name": product_name,
                    "product_uom_qty": line_item.quantity,
                }
            )

        logger.info("Converted order lines: %s", json.dumps(order_lines))
        return order_lines

    def _get_carrier_id(self, order: Order) -> int:
        """Lookup and return Odoo delivery carrier ID by shipment type.

        Args:
            order: Order with shipment_type.

        Returns:
            Odoo carrier record ID.

        Raises:
            ValueError: If shipment_type is empty.
            SaleError: If carrier not found in Odoo.
        """
        carrier_name = order.shipment_type
        if not carrier_name.strip():
            raise ValueError("Shipment type is required in order")

        logger.info("Get carrier ID for name: %s", carrier_name)
        result = self._call(
            model="delivery.carrier",
            method="search_read",
            query_data=[
                [["company_id", "=", order.administration_id], ["name", "ilike", carrier_name]]
            ],
            query_options={"fields": ["id"], "limit": 1},
        )

        if not (
            result
            and isinstance(result, list)
            and isinstance(result[0], dict)
            and (carrier_id := result[0].get("id", None))
            and isinstance(carrier_id, int)
            and carrier_id > 0
        ):
            raise SaleError(f"Carrier '{carrier_name}' not found in Odoo", order.remote_order_id)

        logger.info("Found carrier ID %d for name: %s", carrier_id, carrier_name)
        return carrier_id

    def create_sale(self, order: Order) -> int:
        """Create Odoo sale order for order, or return existing sale ID.

        Args:
            order: Order with all required fields (customer_id, line_items, etc.).

        Returns:
            Odoo sale.order record ID.

        Raises:
            SaleError: If sale creation fails.
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
        # Odoo expects order lines in a special format for creation: a list of (0, 0, {line_data}) tuples
        order_lines = [(0, 0, line) for line in self._convert_order_lines(order)]
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
                    "order_line": order_lines,
                    "state": "draft",
                    "commitment_date": order.ship_at.strftime("%Y-%m-%d"),
                    "carrier_id": self._get_carrier_id(order),
                    "x_remote_delivery_instructions": order.delivery_instructions or None,
                    "x_remote_order_id": order.remote_order_id,
                    "x_remote_order_provider": order.order_provider,
                }
            ],
        )

        if not isinstance(sale_id, int):
            raise SaleError("Failed to create sale", order.remote_order_id)

        logger.info("Created sale with ID %d for order %s", sale_id, order.remote_order_id)
        return sale_id

    def confirm_sale(self, order: Order) -> None:
        """Call Odoo to confirm the sale for `order`; raise `SaleError` on failure."""
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
        """Return True if sale in Odoo contains the expected order lines."""
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
        """Update the sale's shipping contact in Odoo with `order` data."""
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

    def update_delivery_instructions(self, order: Order) -> None:
        """Write `order.delivery_instructions` to the sale in Odoo if present."""
        if not order.delivery_instructions.strip():
            logger.info("No delivery instructions to update for order %s", order.remote_order_id)
            return

        logger.info("Update delivery instructions for order %s", order.remote_order_id)
        sale_data = self._get_sale_data(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError(
                "Cannot update delivery instructions for non-existent sale", order.remote_order_id
            )

        sale_id = sale_data["id"]
        result = self._call(
            model="sale.order",
            method="write",
            query_data=[[sale_id], {"x_remote_delivery_instructions": order.delivery_instructions}],
        )
        if not bool(result):
            raise SaleError(
                f"Failed to update delivery instructions for sale {sale_id}", order.remote_order_id
            )

        logger.info(
            "Delivery instructions updated for sale ID %d (order %s)",
            sale_id,
            order.remote_order_id,
        )

    def get_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Return list of completed sale ids and remote_order_ids for `order_provider`."""
        logger.info("Get completed sales for order provider: %s", order_provider)
        result = self._call(
            model="sale.order",
            method="search_read",
            query_data=[
                [
                    ["delivery_status", "=", "full"],
                    ["state", "=", "sale"],
                    ["x_remote_order_provider", "=", order_provider],
                    ["x_remote_notified_completion", "=", False],
                ]
            ],
            query_options={"fields": ["id", "x_remote_order_id"]},
        )

        if not (
            result
            and isinstance(result, list)
            and all(
                isinstance(item, dict) and "id" in item and "x_remote_order_id" in item
                for item in result
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
        return [(item["id"], item["x_remote_order_id"]) for item in result]

    def get_shipping_info(self, order: Order) -> list[dict[str, Any]]:
        """Query Odoo for shipment records and return simplified shipping info list."""
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
        """Return serial numbers grouped by `order.line_items` remote IDs."""
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
            return {li.line_id: [] for li in order.line_items}

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
            serials_by_line_item[li.line_id] = serials_by_product.get(li.product_code, [])[
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
        """Perform authenticated JSON-RPC call to Odoo and return `result`."""
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
        response = self.session.post(f"{self.base_url}/jsonrpc", json=payload, timeout=(5, 30))
        response.raise_for_status()
        data = response.json()

        if error := data.get("error"):
            message = f"Odoo JSON-RPC error: {error.get('message')} ({error.get('data', {}).get('message')})"
            logger.warning(
                "%s, model=%s, method=%s, data=%s",
                message,
                model,
                method,
                error.get("data"),
            )
            raise SaleError(message)
        return data.get("result")
