"""New sale order creation and processing use case.

Create new sales in Odoo from orders received from multiple service providers.
"""

import shutil
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path

from src.app.errors import SaleError, get_error_store
from src.app.registry import (
    get_artwork_services,
    get_order_services,
    get_sale_services,
    get_use_cases,
)
from src.config import get_config
from src.domain import IArtworkService, IOrderService, IRegistry, ISaleService, Order, OrderStatus

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class NewSaleUseCase:
    """Use case for creating and processing new sales from orders.

    Orchestrates order persistence, sale creation, artwork retrieval, and confirmation.
    Order-level errors are caught and stored without stopping other orders.
    """

    order_services: IRegistry[IOrderService] = field(default_factory=get_order_services)
    artwork_services: IRegistry[IArtworkService] = field(default_factory=get_artwork_services)
    sale_services: IRegistry[ISaleService] = field(default_factory=get_sale_services)
    open_orders_dir: Path = field(default_factory=lambda: Path(get_config().open_orders_dir))

    @classmethod
    def register(cls, name: str) -> None:
        """Factory method to create and register a NewSaleUseCase instance."""
        use_case = cls()
        get_use_cases().register(name, use_case)

    def execute(self) -> None:
        """Create new sales from orders across all registered providers.

        Multi-provider orchestration workflow:
        1. For each order service provider (e.g., HARMAN B2B, HARMAN B2C, Camelbak):
           a. Read all orders from that provider
           b. For each order:
              i. Persist order with NEW status
              ii. For each sale service provider (e.g., ODOO):
                  - Search for existing sale matching order ID and provider
                  - If not found: Create new sale with order details
                  - If found: Update sale if order data changed, validate line items
              iii. Persist order with CREATED status
              iv. Retrieve artwork files from artwork service
              v. Organize placement files to order directory
              vi. Persist order with ARTWORK and then CONFIRMED status

        Errors at order level are caught and stored without stopping processing of other orders.
        This multi-provider coordination allows graceful degradation if one provider is down.
        """
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

                    for sale_service_name, sale_service in self.sale_services.items():
                        logger.info(
                            "Check if sale exists for order %s in %s service...",
                            order.remote_order_id,
                            sale_service_name,
                        )
                        if not sale_service.search_sale(order):
                            # no sale for this order, create it
                            sale_id, sale_name = sale_service.create_sale(order)
                            order.set_sale_id(sale_id)
                            order.set_sale_name(sale_name)
                        elif order_service.should_update_sale(order):
                            # sale exists but order data has changed, update it
                            if not sale_service.sale_has_expected_order_lines(order):
                                # order lines do not match expected lines for this order, raise error
                                raise SaleError(
                                    "Existing sale order lines do not match expected lines",
                                    order.remote_order_id,
                                )
                            sale_service.update_contact(order)
                            sale_service.update_sale(order)

                    # when we reach this point, the order is in an expected state
                    order_service.persist_order(order, OrderStatus.CREATED)

                    # get artwork for the order
                    if artwork_service := order_service.artwork_service:
                        artwork_files = artwork_service.get_artwork(order)
                        self.organize_placement_files(order, artwork_files)
                        order_service.persist_order(order, OrderStatus.ARTWORK)

                    # persist the order as confirmed after all processing is done
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
