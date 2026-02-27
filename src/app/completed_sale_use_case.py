"""New sale orders use case."""

from dataclasses import dataclass
from logging import getLogger

from src.app.errors import SaleError
from src.domain.order import OrderStatus
from src.interfaces.ierror_queue import IErrorQueue
from src.interfaces.iorder_service import IOrderService
from src.interfaces.iregistry import IRegistry
from src.interfaces.isale_service import ISaleService

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
                        if isinstance(exc, SaleError):
                            self.error_queue.put(exc)
                        else:
                            self.error_queue.put(
                                SaleError(
                                    message=f"{exc!s} (Provider: {order_provider})",
                                    order_id=remote_order_id,
                                )
                            )
            except Exception as exc:
                logger.exception("Error completing sales for provider %s: %s", order_provider, exc)
                if isinstance(exc, SaleError):
                    self.error_queue.put(exc)
                else:
                    self.error_queue.put(
                        SaleError(
                            message=f"{exc!s} (Provider: {order_provider})",
                            order_id=None,
                        )
                    )
