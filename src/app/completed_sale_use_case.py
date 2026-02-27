"""Completed sale orders use case."""

from dataclasses import dataclass
from logging import getLogger

from src.app.error_handler import ErrorHandler
from src.app.errors import SaleError
from src.domain import OrderStatus
from src.interfaces import IErrorQueue, IOrderService, IRegistry, ISaleService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletedSaleUseCase:
    """Use case for completing sale orders."""

    order_services: IRegistry[IOrderService]
    sale_service: ISaleService
    error_queue: IErrorQueue

    def execute(self) -> None:
        """Complete sales for all order services."""
        logger.info("Complete sales for all order services...")
        error_handler = ErrorHandler(self.error_queue)
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
                        error_handler.handle_provider_error(
                            exc,
                            order_provider,
                            remote_order_id,
                            "Error completing sale",
                        )
            except Exception as exc:
                error_handler.handle_provider_error(
                    exc,
                    order_provider,
                    None,
                    "Error completing sales",
                )
