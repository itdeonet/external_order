"""New sale orders use case."""

import shutil
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from src.app.errors import SaleError
from src.domain.interfaces.iartwork_service import IArtworkService
from src.domain.interfaces.ierror_queue import IErrorQueue
from src.domain.interfaces.iorder_service import IOrderService
from src.domain.interfaces.iregistry import IRegistry
from src.domain.interfaces.isales_service import ISalesService
from src.domain.order import Order, OrderStatus

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class NewSaleUseCase:
    """Use case for creating new sale orders."""

    order_services: IRegistry[IOrderService]
    artwork_services: IRegistry[IArtworkService]
    sales_service: ISalesService
    error_queue: IErrorQueue
    open_orders_dir: Path

    def create_sales(self) -> None:
        """Create sales from all order services."""
        for order_service_name, order_service in self.order_services.items():
            logger.info("Create sales from %s service...", order_service_name)

            # process orders
            for order in order_service.get_orders(self.error_queue):
                try:
                    logger.info(
                        "Process order %s from %s service.",
                        order.remote_order_id,
                        order_service_name,
                    )
                    order_service.persist_order(order, OrderStatus.NEW)

                    # create or update sale for the order
                    self.create_or_update_sale(order)
                    order_service.persist_order(order, OrderStatus.CREATED)

                    # get artwork for the order
                    artwork_service = order_service.get_artwork_service(
                        order, self.artwork_services
                    )
                    self.get_artwork(order, artwork_service)
                    order_service.persist_order(order, OrderStatus.ARTWORK)
                    self.sales_service.confirm_sale(order.id)
                    order_service.persist_order(order, OrderStatus.CONFIRMED)

                except Exception as exc:
                    logger.error(
                        "Error processing order %s from %s service: %s",
                        order.remote_order_id,
                        order_service_name,
                        str(exc),
                    )
                    self.error_queue.put(exc)

    def create_or_update_sale(self, order: Order) -> None:
        """Update an existing sale for the given order."""
        sale = self.sales_service.get_sale(order)
        if not sale:
            logger.info("Creating new sale for order %s", order.remote_order_id)
            order.set_id(self.sales_service.create_sale(order))
            return

        logger.info("Update sale %s for order %s", sale["id"], order.remote_order_id)
        order.set_id(int(sale["id"]))
        if self.sales_service.verify_sale_quantities(order, sale):
            self.sales_service.update_contact(order)
            self.sales_service.confirm_sale(order.id)
        else:
            logger.warning(
                "Sale order line quantities do not match for order %s", order.remote_order_id
            )
            raise SaleError("Sale order line quantities do not match", order.remote_order_id)

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
