"""New sale order creation and processing use case.

This module handles the creation of new sales in Odoo from orders received from
multiple order service providers. It orchestrates order persistence, sale creation,
contact updates, artwork retrieval, and sale confirmation across the entire order
lifecycle. Errors at the order level are caught and stored without stopping
processing of other orders.
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

    This use case processes orders from multiple service providers through the full
    order-to-sale workflow:
    1. Read orders from each service provider
    2. Persist order and create corresponding sale in Odoo
    3. Handle existing sales (create or update based on order lines)
    4. Retrieve and organize artwork for the order
    5. Confirm the sale
    6. Persist final order status

    Errors are caught at the individual order level and stored, allowing other orders
    to be processed normally. Processed artwork is organized by customer ID in the
    open orders directory.

    Attributes:
        order_services: Registry of order service providers to process.
        artwork_services: Registry of artwork services available for orders.
        sale_service: Service for creating and managing sales in Odoo.
        open_orders_dir: Directory path where processed artwork is stored.
    """

    order_services: IRegistry[IOrderService]
    artwork_services: IRegistry[IArtworkService]
    sale_service: ISaleService
    open_orders_dir: Path

    def execute(self) -> None:
        """Process orders from all registered service providers and create sales.

        For each order service provider:
        1. Read all orders from the provider
        2. For each order:
           - Persist with NEW status
           - Create new sale if it doesn't exist
           - Update contact info if sale exists with expected lines
           - Raise error if sale exists with mismatched lines
           - Retrieve artwork using the service specified by the order
           - Persist with ARTWORK status
           - Confirm the sale in Odoo
           - Persist with CONFIRMED status

        Order-level errors (create, update, confirm failures) are caught, logged,
        and stored. Processing continues with the next order.

        All exceptions are stored in the ErrorStore singleton for later review.
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

                    if not self.sale_service.is_sale_created(order):
                        # no sale for this order, create it
                        self.sale_service.create_sale(order)
                    elif self.sale_service.has_expected_order_lines(order):
                        # sale already exists and has expected order lines, update contact info
                        self.sale_service.update_contact(order)
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
        """Download and organize artwork files for an order.

        Retrieves artwork from the service and processes placement files by:
        1. Downloading all files for the order
        2. Filtering for files named with '_placement' suffix
        3. Organizing placement files into subdirectories named by customer ID
        4. Logging all operations for tracking

        Args:
            order: The order to retrieve artwork for.
            artwork_service: The service to use for artwork retrieval. If None,
                returns empty list and logs a warning.

        Returns:
            A list of Path objects for all downloaded files, including placement
            and non-placement files. Empty list if no service is available.
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
