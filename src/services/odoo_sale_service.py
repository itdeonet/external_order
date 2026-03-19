"""Odoo sales service: create, confirm and query sales via JSON-RPC.

Utilities for mapping domain `Order` objects to Odoo `sale.order` records.
"""

import copy
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

import requests

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.app.registry import get_sale_services
from src.config import get_config
from src.domain import Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooSaleService:
    """Manage sales: map `Order` to `sale.order` and call RPC methods."""

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

    @classmethod
    def register(cls, name: str, session: requests.Session) -> None:
        """Factory method to create and register an OdooSaleService instance."""
        sale_service = cls(session=session)
        get_sale_services().register(name, sale_service)

    def search_sale(self, order: Order) -> dict[str, Any]:
        """Search sale matching order's remote_order_id.

        Args:
            order: Order to search for.

        Returns:
            Sale dict if found, else empty dict.
        """
        logger.info("Search sale for order: %s", order.remote_order_id)
        result = self._call(
            model="sale.order",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    ["id", "=", order.sale_id]
                    if order.sale_id
                    else ["x_remote_order_id", "=", order.remote_order_id],
                    ["x_remote_order_provider", "=", order.order_provider],
                ]
            ],
            query_options={"limit": 1},
        )

        if not (result and isinstance(result, list) and isinstance(result[0], dict)):
            return {}

        order.set_sale_id(result[0].get("id", 0))
        order.set_sale_name(result[0].get("name", ""))
        return result[0]

    def _search_country_id(self, country_code: str) -> int:
        """Search sale system country ID by ISO country code.

        Args:
            country_code: ISO 2-letter country code.

        Returns:
            Country record ID.

        Raises:
            SaleError: If country code not found.
        """
        logger.info("Search country ID for country code: %s", country_code)
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
            raise SaleError(f"Country code '{country_code}' not found")

        logger.info("Found country ID %d for country code %s", country_id, country_code)
        return country_id

    def _search_state_id(self, country_id: int, state: str) -> int:
        """Search sale system state ID by country ID and state name.

        Args:
            country_id: Odoo country record ID.
            state: State name to search for (case-insensitive).

        Returns:
            State record ID, or 0 if not found.
        """
        logger.info("Search state ID for country_id=%s region=%s", country_id, state)
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

    def _load_contact_data_from_order(self, order: Order) -> dict[str, Any]:
        """Map order ship_to info to contact dict data.

        Args:
            order: Order

        Returns:
            Dict of fields ready for search/create/write.
        """
        logger.info("Load contact data from order: %s", order.remote_order_id)
        ship_to = order.ship_to
        country_id = self._search_country_id(ship_to.country_code)
        state_id = (
            self._search_state_id(country_id, ship_to.state)
            if ship_to.state and ship_to.state.strip()
            else 0
        )
        # Note: the customer's company name is mapped to "deonet_other_company"
        contact_data = {
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
        logger.info("Loaded contact data for order %s: %s", order.remote_order_id, contact_data)
        return contact_data

    def _create_contact(self, order: Order) -> int:
        """Create  a new or return existing contact.

        Args:
            order: Order with shipping and contact info.

        Returns:
            Contact ID.

        Raises:
            SaleError: If contact creation fails.
        """
        logger.info("Create contact for order: %s", order.remote_order_id)

        # build contact data from the order's ship_to information
        contact_data = self._load_contact_data_from_order(order)

        # check if a contact with the same fields already exists
        logger.info("Search existing contact for order %s", order.remote_order_id)
        result = self._call(
            model="res.partner",
            method="search_read",
            query_data=[[[key, "=", value] for key, value in contact_data.items()]],
            query_options={"fields": ["id"], "limit": 1},
        )

        if result and isinstance(result, list) and "id" in result[0]:
            contact_id = int(result[0]["id"])
            logger.info("Contact exists with ID %d", contact_id)
            return contact_id

        # create a new contact if it doesn't exist
        logger.info("Contact not found, create new contact for order %s", order.remote_order_id)
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
                    f"Product search for {line_item.product_code} failed",
                    order.remote_order_id,
                )

            order_lines.append(
                {
                    "product_id": product_id,
                    "name": product_name,
                    "product_uom_qty": line_item.quantity,
                }
            )

        logger.info("Converted order lines: %s", order_lines)
        return order_lines

    def _search_carrier_id(self, order: Order) -> int:
        """Search carrier ID by shipment type.

        Args:
            order: Order with shipment_type.

        Returns:
            Odoo carrier record ID.

        Raises:
            ValueError: If shipment_type is empty.
            SaleError: If carrier not found in Odoo.
        """
        if not order.shipment_type.strip():
            raise ValueError("Shipment type is required in order")

        logger.info("Search carrier ID for: %s", order.shipment_type)
        result = self._call(
            model="delivery.carrier",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    ["name", "ilike", order.shipment_type],
                ]
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
            raise SaleError(
                f"Carrier for search '{order.shipment_type}' not found", order.remote_order_id
            )

        logger.info("Found carrier ID %d for search: %s", carrier_id, order.shipment_type)
        return carrier_id

    def create_sale(self, order: Order) -> tuple[int, str]:
        """Create sale for order, or return existing sale ID.

        Args:
            order: Order with all required fields (customer_id, line_items, etc.).

        Returns:
            Sale ID.

        Raises:
            SaleError: If sale creation fails.
        """
        logger.info("Create sale for order: %s", order.remote_order_id)
        logger.info("Search sale for order %s", order.remote_order_id)
        if sale_data := self.search_sale(order):
            logger.info(
                "Sale exists for order %s from provider %s with (ID, name) (%s, %s)",
                order.remote_order_id,
                order.order_provider,
                sale_data["id"],
                sale_data["name"],
            )
            return sale_data["id"], sale_data["name"]

        logger.info("Sale not found for order %s, create new sale", order.remote_order_id)
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
                    "state": "sale",
                    "commitment_date": order.ship_at,
                    "carrier_id": self._search_carrier_id(order),
                    "x_remote_delivery_instructions": order.delivery_instructions or None,
                    "x_remote_order_id": order.remote_order_id,
                    "x_remote_order_provider": order.order_provider,
                }
            ],
        )

        if not isinstance(sale_id, int):
            raise SaleError("Failed to create sale", order.remote_order_id)

        if sale_data := self.search_sale(order):
            logger.info(
                "Sale created for order %s from provider %s with (ID, name) (%s, %s)",
                order.remote_order_id,
                order.order_provider,
                sale_data["id"],
                sale_data["name"],
            )
            return sale_data["id"], sale_data["name"]
        else:
            raise SaleError("Sale created but not found on search", order.remote_order_id)

    def sale_has_expected_order_lines(self, order: Order) -> bool:
        """Does the sale for the given order contain the expected order lines."""
        logger.info(
            "Does the sale for order %s from provider %s have the expected order lines?",
            order.remote_order_id,
            order.order_provider,
        )
        sale_data = self.search_sale(order)
        if not sale_data or "id" not in sale_data or sale_data["id"] == 0:
            raise SaleError("Sale not found", order.remote_order_id)

        # read the sale's order lines as tuples of (product_id, quantity)
        sale_lines = {
            (line["product_id"][0], line["product_uom_qty"])
            for line in self._call(
                model="sale.order.line",
                method="search_read",
                query_data=[[["order_id", "=", sale_data["id"]]]],
                query_options={"fields": ["product_id", "product_uom_qty"]},
            )
        }

        # convert the order's line items to tuples of (product_id, quantity) for comparison
        order_lines = {
            (li["product_id"], li["product_uom_qty"]) for li in self._convert_order_lines(order)
        }

        # B2B sales are manually created and may have more lines than the order confirmation
        # So we check that all order lines are in the sale, but allow the sale to have extra lines.
        result = order_lines.issubset(sale_lines)
        logger.info(
            "Order lines for order %s match expected lines: %s", order.remote_order_id, result
        )
        return result

    def update_contact(self, order: Order) -> None:
        """Update the sale's contact with `order` data."""
        logger.info("Update contact for order %s", order.remote_order_id)
        sale_data = self.search_sale(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError("Sale not found", order.remote_order_id)

        # partner_shipping_id is in format [contact_id, contact_name]
        contact_id: int = sale_data.get("partner_shipping_id", [0, ""])[0]
        if not contact_id:
            raise SaleError("Sale has no shipping contact to update", order.remote_order_id)

        contact_data = self._load_contact_data_from_order(order)
        result = self._call(
            model="res.partner",
            method="write",
            query_data=[[contact_id], contact_data],
        )
        if not bool(result):
            raise SaleError(f"Failed to update contact {contact_id}", order.remote_order_id)

        logger.info("Contact ID %d updated (order %s)", contact_id, order.remote_order_id)

    def update_sale(self, order: Order) -> None:
        """Update sale from `order` data."""
        logger.info("Update sale for order %s", order.remote_order_id)
        sale_data = self.search_sale(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError("Sale not found", order.remote_order_id)

        sale_id = sale_data["id"]
        result = self._call(
            model="sale.order",
            method="write",
            query_data=[
                [sale_id],
                {
                    "x_remote_delivery_instructions": order.delivery_instructions or None,
                    "x_remote_order_id": order.remote_order_id,
                    "x_remote_order_provider": order.order_provider,
                },
            ],
        )
        if not bool(result):
            raise SaleError(
                f"Failed to set delivery instructions for sale {sale_id}",
                order.remote_order_id,
            )

        logger.info(
            "Delivery instructions set for sale ID %d (order %s)",
            sale_id,
            order.remote_order_id,
        )

    def search_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Search completed sales for given order provider.

        Returns list of tuples containing sale_ids and remote_order_ids.
        """
        logger.info("Search completed sales for order provider: %s", order_provider)
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
            result,
        )
        return [(item["id"], item["x_remote_order_id"]) for item in result]

    def mark_sale_notified(self, sale_id: int) -> None:
        """Mark sale as notified for completed sale notifications."""
        logger.info("Mark sale ID %d as notified", sale_id)
        result = self._call(
            model="sale.order",
            method="write",
            query_data=[[sale_id], {"x_remote_notified_completion": True}],
        )
        if not bool(result):
            raise SaleError(f"Failed to mark sale {sale_id} as notified")

        logger.info("Sale ID %d marked as notified", sale_id)

    def search_shipping_info(self, order: Order) -> list[dict[str, Any]]:
        """Search for shipment records and return simplified shipping info list."""
        logger.info("Search shipping information for order: %s", order.remote_order_id)
        sale_data = self.search_sale(order)
        result = self._call(
            model="stock.picking",
            method="search_read",
            query_data=[
                [
                    ["carrier_id", "!=", False],
                    ["company_id", "=", order.administration_id],
                    ["sale_id", "=", sale_data.get("id", 0)],
                    ["state", "=", "done"],
                    ["picking_type_code", "=", "outgoing"],
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
            shipping_info,
        )
        return shipping_info

    def search_serials_by_line_item(self, order: Order) -> dict[str, list[str]]:
        """Search for serial numbers grouped by `order.line_items` remote IDs."""
        logger.info("Search serial numbers for order: %s", order.remote_order_id)
        sale_data = self.search_sale(order)
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
            serials_by_line_item,
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
        config = get_config()
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

        payload_copy: dict[str, Any] = copy.deepcopy(payload)
        payload_copy.get("params", {}).get("args", [])[2] = "********"  # mask password for logging
        logger.debug("Make JSON_RPC call with payload: %s", payload_copy)
        config = get_config()
        url = f"{self.base_url.rstrip('/')}/jsonrpc"
        timeout = config.odoo_request_timeout

        try:
            response = self.session.post(url=url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as exc:
            raise SaleError(
                message=f"Odoo JSON-RPC error: {exc.response.status_code} {exc.response.reason}",
                order_id=None,
            ) from exc

        if error := data.get("error"):
            data = error.get("data", {})
            message = f"Odoo JSON-RPC error: {error.get('message')} ({data.get('message')})"
            logger.warning(
                "%s, model=%s, method=%s, data=%s",
                message,
                model,
                method,
                error.get("data"),
            )
            raise SaleError(message)
        return data.get("result")
