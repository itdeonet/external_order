"""New sale order creation and processing use case.

Create new sales in Odoo from orders received from multiple service providers.
"""

import shutil
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from src.app.errors import SaleError, get_error_store
from src.domain import IArtworkService, IOrderService, IRegistry, ISaleService, Order, OrderStatus

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

                    if not self.sale_service.search_sale(order):
                        # no sale for this order, create it
                        order.set_sale_id(self.sale_service.create_sale(order))
                    elif order_service.should_update_sale(order):
                        # sale exists but order data has changed, update it
                        if not self.sale_service.sale_has_expected_order_lines(order):
                            # order lines do not match expected lines for this order, raise error
                            raise SaleError(
                                "Existing sale order lines do not match expected lines",
                                order.remote_order_id,
                            )
                        self.sale_service.update_contact(order)
                        self.sale_service.set_delivery_instructions(order)

                    # when we reach this point, the order is in an expected state
                    order_service.persist_order(order, OrderStatus.CREATED)

                    # get artwork for the order
                    if artwork_service := order_service.get_artwork_service(
                        order, self.artwork_services
                    ):
                        artwork_files = artwork_service.get_artwork(order)
                        self.organize_placement_files(order, artwork_files)
                        order_service.persist_order(order, OrderStatus.ARTWORK)

                    # confirm the sale in the sales system
                    self.sale_service.confirm_sale(order)
                    order_service.persist_order(order, OrderStatus.CONFIRMED)

                except Exception as exc:
                    logger.exception(
                        "Error processing order %s from %s service",
                        order.remote_order_id,
                        order_service_name,
                    )
                    get_error_store().add(exc)

    def organize_placement_files(self, order: Order, artwork_files: list[Path]) -> list[Path]:
        """Organize placement files by sale.

        Returns empty list if no artwork service is available.
        """
        if not artwork_files:
            logger.warning("No artwork files to organize for order %s.", order.remote_order_id)
            return []

        placement_files: list[Path] = []
        for file in artwork_files:
            name_parts = file.stem.split("_")
            if name_parts[-1].lower() == "placement":
                # copy the file to the open orders directory with a subdirectory for the order
                order_dir = self.open_orders_dir / name_parts[0]
                order_dir.mkdir(parents=True, exist_ok=True)
                copy_path = order_dir / file.name
                shutil.copy2(file, copy_path)
                logger.info("Placement file %s copied to %s.", file, copy_path)
                placement_files.append(copy_path)
        return placement_files
