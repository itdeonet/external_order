"""Odoo service implementation."""

import json
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

import httpx

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.domain.order import Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooSaleService:
    """Service for managing sales in Odoo."""

    auth: OdooAuth
    engine: httpx.Client
    _id_counter: Iterator[int] = field(default_factory=lambda: iter(range(1, 1000000)), init=False)

    def __post_init__(self) -> None:
        """Initialize the Odoo RPC client."""
        if not (self.auth and isinstance(self.auth, OdooAuth)):
            raise ValueError("Odoo authentication information is missing or invalid")
        if not (self.engine and isinstance(self.engine, httpx.Client)):
            raise ValueError("Odoo engine is missing or invalid")
        if not (self.engine.base_url):
            raise ValueError("Odoo engine base URL is not set")

    def _get_sale_data(self, order: Order) -> dict[str, Any]:
        """Get the OdooSale object for the given order."""
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
        """Check if a sale/quote has been created for the given order."""
        logger.info("Is order %s created?", order.remote_order_id)
        result = bool(self._get_sale_data(order).get("id", 0))
        logger.info("Sale for order %s created: %s", order.remote_order_id, result)
        return result

    def _get_country_id(self, country_code: str) -> int:
        """Resolve ISO country code to res.country id."""
        logger.info("Get country ID for country code: %s", country_code)
        result = self._call(
            model="res.country",
            method="search_read",
            query_data=[[["code", "=", country_code.strip().upper()[:2]]]],
            query_options={"fields": ["id"], "limit": 1},
        )

        if not (result and isinstance(result, list) and "id" in result[0]):
            raise SaleError(f"Country code '{country_code}' not found")

        country_id = int(result[0]["id"])
        logger.info("Found country ID %d for country code %s", country_id, country_code)
        return country_id

    def _get_state_id(self, country_id: int, state: str) -> int:
        """Resolve a region/state to res.country.state id."""
        logger.info("Get state ID for country_id=%s region=%s", country_id, state)
        if not (state := state.strip()):
            return 0

        result = self._call(
            model="res.country.state",
            method="search_read",
            query_data=[[["country_id", "=", country_id], ["name", "ilike", state]]],
            query_options={"fields": ["id"], "limit": 1},
        )

        if not (result and isinstance(result, list) and "id" in result[0]):
            logger.warning("State '%s' not found for country_id %d, returning 0", state, country_id)
            return 0

        state_id = int(result[0]["id"])
        logger.info("Found state ID %d for country_id=%s region=%s", state_id, country_id, state)
        return state_id

    def _get_contact_data_from_order(self, order: Order) -> dict[str, Any]:
        """Build contact data from the order's ship_to information."""
        logger.info("Build contact data from order: %s", order.remote_order_id)
        ship_to = order.ship_to
        country_id = self._get_country_id(ship_to.country_code)
        state_id = (
            self._get_state_id(country_id, ship_to.state)
            if ship_to.state and ship_to.state.strip()
            else None
        )
        return {
            "company_id": int(order.administration_id),
            "parent_id": int(order.customer_id),
            "ref": ship_to.remote_customer_id,
            "name": ship_to.contact_name,
            "company_name": ship_to.company_name,
            "type": "other",
            "is_company": True,
            "street": ship_to.street1,
            "street2": ship_to.street2,
            "city": ship_to.city,
            "state_id": state_id,
            "zip": ship_to.postal_code,
            "country_id": country_id,
            "phone": ship_to.phone,
            "email": ship_to.email,
            "x_remote_source": order.order_provider,
        }

    def _create_contact(self, order: Order) -> int:
        """Create or update the contact for the given order and return its ID."""
        logger.info("Create contact for order: %s", order.remote_order_id)

        # build contact data from the order's ship_to information
        contact_data = self._get_contact_data_from_order(order)

        # check if a contact with the same reference already exists for the parent customer
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
        """Convert the order lines to the format required by Odoo."""
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
                and "id" in result[0]
                and "name" in result[0]
            ):
                raise SaleError(f"Product {line_item.product_code} not found")

            order_lines.append(
                {
                    "product_id": result[0]["id"],
                    "name": result[0]["name"],
                    "product_uom_qty": line_item.quantity,
                }
            )

        logger.info("Converted order lines: %s", json.dumps(order_lines))
        return order_lines

    def _get_carrier_id(self, order: Order) -> int:
        """Resolve delivery.carrier by name."""
        carrier_name = order.shipment_type
        if not carrier_name.strip():
            raise ValueError("Carrier name is empty")

        logger.info("Get carrier ID for name: %s", carrier_name)
        result = self._call(
            model="delivery.carrier",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    ["name", "=ilike", carrier_name],
                ]
            ],
            query_options={"fields": ["id", "name"], "limit": 1},
        )

        if not (
            result
            and isinstance(result, list)
            and isinstance(result[0], dict)
            and "id" in result[0]
        ):
            raise SaleError(f"Carrier '{carrier_name}' not found in Odoo")

        carrier_id = int(result[0]["id"])
        logger.info("Found carrier ID %d for name: %s", carrier_id, carrier_name)
        return carrier_id

    def create_sale(self, order: Order) -> int:
        """Create a sale for the given order and return its ID."""
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
            raise SaleError(f"Failed to create sale for order {order.remote_order_id}")

        logger.info("Created sale with ID %d for order %s", sale_id, order.remote_order_id)
        return sale_id

    def confirm_sale(self, order: Order) -> None:
        """Confirm the sale for the given order."""
        sale_data = self._get_sale_data(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError("Cannot confirm sale that does not exist in Odoo")

        sale_id = sale_data["id"]
        logger.info("Confirm sale with id: %s for order: %s", sale_id, order.remote_order_id)
        result = self._call(
            model="sale.order",
            method="action_confirm",
            query_data=[[sale_id]],
        )

        if not bool(result):
            raise SaleError(f"Failed to confirm sale id {sale_id}")

        logger.info("Sale with id %d confirmed successfully", sale_id)

    def has_expected_order_lines(self, order: Order) -> bool:
        """Verify that the sale has the same order line quantities as the given order."""
        logger.info(
            "Check if sale for order %s from provider %s has expected order lines in Odoo",
            order.remote_order_id,
            order.order_provider,
        )
        sale_data = self._get_sale_data(order)
        if not sale_data or "id" not in sale_data or sale_data["id"] == 0:
            raise SaleError("Cannot check order lines for sale that does not exist in Odoo")

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

        result = odoo_lines == order_lines or order_lines.issubset(odoo_lines)
        logger.info(
            "Order lines for order %s match expected lines: %s", order.remote_order_id, result
        )
        return result

    def update_contact(self, order: Order) -> None:
        """Update the contact information for the given order."""
        logger.info("Update contact information for order %s", order.remote_order_id)
        sale_data = self._get_sale_data(order)
        if not (sale_data and "id" in sale_data and sale_data["id"] != 0):
            raise SaleError("Cannot update contact for sale that does not exist")

        contact_id: int = sale_data.get("partner_shipping_id", [0, ""])[0]
        if not contact_id:
            raise SaleError("Sale does not have a shipping contact to update")

        contact_data = self._get_contact_data_from_order(order)
        result = self._call(
            model="res.partner",
            method="write",
            query_data=[[contact_id], contact_data],
        )
        if not bool(result):
            raise SaleError(
                f"Failed to update contact id {contact_id} for order {order.remote_order_id}"
            )

        logger.info(
            "Contact with ID %d updated successfully for order %s",
            contact_id,
            order.remote_order_id,
        )

    def get_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Get a list of completed sales for the given order provider."""
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
        """Get the shipping information for the given order."""
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
        """Get the serial numbers for the given order by line item."""
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
            return {li.remote_line_id: [] for li in order.line_items}

        serials_by_product = defaultdict(list)
        for item in result:
            product_name = item["product_id"][1].split()[0][1:-1]
            serials_by_product[product_name].append(item["serial"])

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
        """Execute a JSON-RPC call to the Odoo server."""
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
