"""Odoo service implementation."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from logging import getLogger
from typing import Any

import httpx

from src.app.errors import SaleError
from src.app.odoo_auth import OdooAuth
from src.domain.line_item import LineItem
from src.domain.order import Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooSalesService:
    """Odoo service implementation."""

    auth: OdooAuth
    engine: httpx.Client
    _id_counter: Iterator[int] = field(default_factory=lambda: iter(range(1, 1000000)), init=False)

    def create_sale(self, order: Order) -> int:
        """Create a draft order for the given order."""
        logger.info("Create a draft sale.order for order: %s", order.remote_order_id)

        order_lines = [self._build_odoo_product_line(li) for li in order.line_items]
        if not (contact_id := self.get_contact_id(order)):
            contact_id = self.create_contact(order)

        sale_id = self._execute_kw(
            model="sale.order",
            method="create",
            query_data=[
                {
                    "partner_id": order.customer_id,
                    "partner_shipping_id": contact_id,
                    "company_id": int(order.administration_id),
                    "client_order_ref": order.description,
                    "pricelist_id": order.pricelist_id,
                    "order_line": order_lines,
                    "state": "sale",
                    "commitment_date": order.ship_at.strftime("%Y-%m-%d"),
                    "carrier_id": self.get_carrier_id(
                        int(order.administration_id), order.shipment_type
                    ),
                    "x_remote_id": order.remote_order_id,
                    "x_remote_source": order.order_provider,
                }
            ],
        )
        if isinstance(sale_id, int):
            self.confirm_sale(sale_id)
            return sale_id
        raise SaleError(f"Failed to create sale.order for order {order.remote_order_id}")

    def confirm_sale(self, sale_id: int) -> None:
        """Confirm order as a sale order."""
        logger.info("Confirm sale.order with id: %s", sale_id)
        result = self._execute_kw("sale.order", "action_confirm", query_data=[[sale_id]])
        if not bool(result):
            raise SaleError(f"Failed to confirm sale.order id {sale_id} in Odoo")

    def get_sale(self, order: Order) -> dict[str, Any]:
        """Get the sale order for the given order, if it exists."""
        logger.info("Get sale.order for remote_order_id: %s", order.remote_order_id)
        result = self._execute_kw(
            model="sale.order",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", order.administration_id],
                    "|",
                    ["x_remote_id", "=", order.remote_order_id],
                    ["name", "=", order.remote_order_id],
                    ["id", "=", order.id],
                ]
            ],
            query_options={"limit": 1},
        )
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return result[0]
        return {}

    def get_completed_sales(self, order_provider: str) -> list[int]:
        """Get a list of completed sales for the given order provider."""
        logger.info("Get completed sales for order provider: %s", order_provider)
        result = self._execute_kw(
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
            query_options={"fields": ["id"]},
        )
        if isinstance(result, list) and all(isinstance(item, int) for item in result):
            return result
        return []

    def _build_odoo_product_line(self, line_item: LineItem) -> dict[str, Any]:
        """Build a single order line dict for Odoo from a LineItem."""
        result = self._execute_kw(
            model="product.product",
            method="search_read",
            query_data=[[["default_code", "=", line_item.product_id]]],
            query_options={"fields": ["id", "name"], "limit": 1},
        )

        if not result or not isinstance(result, list):
            message = f"Product ID {line_item.product_id} not found in Odoo"
            raise SaleError(message)

        product = result[0]
        return {
            "product_id": int(product["id"]),
            "name": product.get("name", line_item.product_id),
            "product_uom_qty": line_item.quantity,
        }

    def get_country_id(self, country_code: str) -> int:
        """Resolve ISO country code to res.country id."""
        logger.info("Get country ID for country code: %s", country_code)
        result = self._execute_kw(
            model="res.country",
            method="search_read",
            query_data=[
                [["code", "=", country_code.strip().upper()[:2]]],
            ],
            query_options={"fields": ["id"], "limit": 1},
        )
        if isinstance(result, list) and result and "id" in result[0]:
            return int(result[0]["id"])
        raise SaleError(f"Country code '{country_code}' not found in Odoo")

    def get_state_id(self, country_id: int, state: str) -> int:
        """Resolve a region/state to res.country.state id."""
        logger.info("Get state ID for country_id=%s region=%s", country_id, state)
        if not (state := state.strip()):
            return 0

        result = self._execute_kw(
            model="res.country.state",
            method="search_read",
            query_data=[[["country_id", "=", country_id], ["name", "ilike", state]]],
            query_options={"fields": ["id"], "limit": 1},
        )
        if isinstance(result, list) and result and "id" in result[0]:
            return int(result[0]["id"])
        return 0

    def get_carrier_id(self, administration_id: int, carrier_name: str) -> int:
        """Resolve delivery.carrier by name."""
        if not carrier_name.strip():
            raise ValueError("Carrier name is empty")

        logger.info("Get carrier ID for name: %s", carrier_name)
        result = self._execute_kw(
            model="delivery.carrier",
            method="search_read",
            query_data=[
                [
                    ["company_id", "=", administration_id],
                    ["name", "=ilike", carrier_name],
                ]
            ],
            query_options={"fields": ["id", "name"], "limit": 1},
        )

        if isinstance(result, list) and result and "id" in result[0]:
            return int(result[0]["id"])
        raise SaleError(f"Carrier '{carrier_name}' not found in Odoo")

    def _build_contact_data(self, order: Order) -> dict[str, Any]:
        """Build parameters for searching, creating and updating a contact."""
        logger.info("Get contact data for order: %s", order.remote_order_id)
        ship_to = order.ship_to

        country_id = self.get_country_id(ship_to.country_code)
        state_id = (
            self.get_state_id(country_id, ship_to.state)
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

    def get_contact_id(self, order: Order) -> int:
        """Get the contact ID for an order."""
        logger.info("Get contact ID for order: %s", order.remote_order_id)
        result = self._execute_kw(
            model="res.partner",
            method="search_read",
            query_data=[[[k, v] for k, v in self._build_contact_data(order).items()]],
            query_options={"fields": ["id"], "limit": 1},
        )
        if isinstance(result, list) and result and "id" in result[0]:
            return int(result[0]["id"])
        return 0

    def create_contact(self, order: Order) -> int:
        """Create a contact linked to a partner."""
        ship_to = order.ship_to
        logger.info(
            "Create contact for: company %s, contact %s, email %s",
            ship_to.company_name,
            ship_to.contact_name,
            ship_to.email,
        )
        contact_id = self._execute_kw(
            model="res.partner",
            method="create",
            query_data=[self._build_contact_data(order)],
        )
        if isinstance(contact_id, int):
            return contact_id
        raise SaleError(f"Failed to create contact for order {order.remote_order_id} in Odoo")

    def update_contact(self, order: Order) -> bool:
        """Update contact for an order in the sales system."""
        logger.info("Update contact for order %s", order.remote_order_id)
        if not (contact_id := self.get_contact_id(order)):
            raise SaleError(f"Could not find contact for order {order.remote_order_id}")

        if result := bool(
            self._execute_kw(
                model="res.partner",
                method="write",
                query_data=[[contact_id], self._build_contact_data(order)],
            )
        ):
            return result
        raise SaleError(f"Failed to update contact for order {order.remote_order_id} in Odoo")

    def verify_sale_quantities(self, order: Order, sale: dict[str, Any]) -> bool:
        """Verify sale order line quantities for an order in the sales system."""
        logger.info("Verify sale order line quantities for order %s", order.remote_order_id)
        if not (sale and isinstance(sale, dict) and "id" in sale):
            raise SaleError(f"Invalid sale data for order {order.remote_order_id}: {sale}")

        # get the existing lines as tuple of (line_id, product_id, quantity) for the sale order
        sale_line_data = {
            (
                str(line["product_id"][1]).split()[0][1:-1],
                int(line["product_uom_qty"]),
            )
            for line in self._execute_kw(
                model="sale.order.line",
                method="search_read",
                query_data=[
                    [["company_id", "=", sale["company_id"], ["order_id", "=", sale["id"]]]]
                ],
                query_options={"fields": ["id", "product_id", "product_uom_qty"]},
            )
        }

        # compare with the line items in the order
        return all(
            (str(line.product_id), line.quantity) in sale_line_data for line in order.line_items
        )

    def _execute_kw(
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
