"""New sale orders use case."""

import shutil
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from src.app.error_handler import ErrorHandler
from src.app.errors import SaleError
from src.domain import Order, OrderStatus
from src.interfaces import IArtworkService, IErrorQueue, IOrderService, IRegistry, ISaleService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class NewSaleUseCase:
    """Use case for creating new sale orders."""

    order_services: IRegistry[IOrderService]
    artwork_services: IRegistry[IArtworkService]
    sale_service: ISaleService
    error_queue: IErrorQueue
    open_orders_dir: Path

    def execute(self) -> None:
        """Create sales from all order services."""
        error_handler = ErrorHandler(self.error_queue)
        for order_service_name, order_service in self.order_services.items():
            logger.info("Create sales from %s service...", order_service_name)

            # process orders
            for order in order_service.read_orders(self.error_queue):
                try:
                    logger.info(
                        "Create sale order %s from %s service.",
                        order.remote_order_id,
                        order_service_name,
                    )
                    order_service.persist_order(order, OrderStatus.NEW)

                    # create or update sale for the order
                    if not self.sale_service.is_sale_created(order):
                        self.sale_service.create_sale(order)
                    elif self.sale_service.has_expected_order_lines(order):
                        self.sale_service.update_contact(order)
                    else:
                        logger.warning(
                            "Sale order line quantities do not match for order %s.",
                            order.remote_order_id,
                        )
                        raise SaleError(
                            "Sale order line quantities do not match", order.remote_order_id
                        )
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
                    error_handler.handle_order_error(
                        exc,
                        order.remote_order_id,
                        order_service_name,
                        "Error processing order",
                    )

    def get_artwork(self, order: Order, artwork_service: IArtworkService | None) -> list[Path]:
        """Get artwork for the given order."""
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
