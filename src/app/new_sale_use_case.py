"""New sale order creation and processing use case.

Create new sales in Odoo from orders received from multiple service providers.
"""

import shutil
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from src.app.errors import ErrorStore, SaleError
from src.domain import Order, OrderStatus
from src.interfaces import IArtworkService, IOrderService, IRegistry, ISaleService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class NewSaleUseCase:
    """Use case for creating and processing new sales from orders.

    Orchestrates order persistence, sale creation, artwork retrieval, and confirmation.
    Order-level errors are caught and stored without stopping other orders.
    """

    order_services: IRegistry[IOrderService]
    artwork_services: IRegistry[IArtworkService]
    sale_service: ISaleService
    open_orders_dir: Path

    def execute(self) -> None:
        """Process all orders and create corresponding sales. Handle errors per-order."""
        for order_service_name, order_service in self.order_services.items():
            logger.info("Create sales from %s service...", order_service_name)

            # process orders
            for order in order_service.read_orders():
                try:
                    logger.info(
                        "Create sale order %s from %s service.",
                        order.remote_order_id,
                        order_service_name,
                    )
                    order_service.persist_order(order, OrderStatus.NEW)

                    if not self.sale_service.is_sale_created(order):
                        # no sale for this order, create it
                        self.sale_service.create_sale(order)
                    elif self.sale_service.has_expected_order_lines(order):
                        # sale already exists and has expected order lines, update info
                        self.sale_service.update_contact(order)
                        self.sale_service.update_delivery_instructions(order)
                    else:
                        # sale already exists but order lines do not match
                        raise SaleError("Sale order lines do not match", order.remote_order_id)

                    # when we reach this point, the order is in an expected state
                    order_service.persist_order(order, OrderStatus.CREATED)

                    # get artwork for the order
                    artwork_service = order_service.get_artwork_service(
                        order, self.artwork_services
                    )
                    self.get_artwork(order, artwork_service)
                    order_service.persist_order(order, OrderStatus.ARTWORK)
                    self.sale_service.confirm_sale(order)
                    order_service.persist_order(order, OrderStatus.CONFIRMED)

                except Exception as exc:
                    logger.exception(
                        "Error processing order %s from %s service",
                        order.remote_order_id,
                        order_service_name,
                    )
                    ErrorStore().add(exc)

    def get_artwork(self, order: Order, artwork_service: IArtworkService | None) -> list[Path]:
        """Download artwork and organize placement files by customer ID.

        Returns empty list if no artwork service is available.
        """
        if not artwork_service:
            logger.warning("No artwork service found for order %s.", order.remote_order_id)
            return []

        logger.info("Get artwork for order %s...", order.remote_order_id)
        files = artwork_service.get_artwork(order)
        logger.info("Downloaded %d files for order %s.", len(files), order.remote_order_id)
        for file in files:
            logger.info("File: %s", file)
            name_parts = file.stem.split("_")
            if name_parts[-1].lower() == "placement":
                # copy the file to the open orders directory with a subdirectory for the order
                order_dir = self.open_orders_dir / name_parts[0]
                order_dir.mkdir(parents=True, exist_ok=True)
                copy_path = order_dir / file.name
                shutil.copy2(file, copy_path)
                logger.info("Placement file %s copied to %s.", file, copy_path)
        return files
