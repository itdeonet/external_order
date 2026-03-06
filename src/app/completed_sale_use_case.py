"""Completed sale orders use case.

Handle completion of sales orders across multiple service providers.
"""

from dataclasses import dataclass
from logging import getLogger

from src.app.errors import ErrorStore, SaleError
from src.domain import OrderStatus
from src.interfaces import IOrderService, IRegistry, ISaleService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletedSaleUseCase:
    """Use case for completing sale orders across multiple order service providers.

    Retrieves completed sales, loads orders, notifies providers, and persists status.
    Handles errors per-provider and per-order without stopping processing.
    """

    order_services: IRegistry[IOrderService]
    sale_service: ISaleService

    def execute(self) -> None:
        """Complete sales for all registered order service providers.

        Handle errors at provider and order levels without stopping processing.
        """
        logger.info("Complete sales for all order services...")
        error_store = ErrorStore()
        for order_provider, order_service in self.order_services.items():
            try:
                logger.info("Complete sales for %s service...", order_provider)
                completed_sales = self.sale_service.get_completed_sales(order_provider)
                for _sale_id, remote_order_id in completed_sales:
                    try:
                        if order := order_service.load_order(remote_order_id):
                            logger.debug("Notify completed sale for order %s", remote_order_id)
                            order_service.notify_completed_sale(order)
                            order_service.persist_order(order, OrderStatus.COMPLETED)
                        else:
                            raise SaleError(
                                message=f"Order with remote ID {remote_order_id} not found",
                                order_id=remote_order_id,
                            )
                    except Exception as exc:
                        logger.exception("Error completing sale for order %s", remote_order_id)
                        error_store.add(exc)
            except Exception as exc:
                logger.exception("Error completing sales for %s service", order_provider)
                error_store.add(exc)
