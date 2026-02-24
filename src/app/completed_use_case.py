"""New sale orders use case."""

from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from src.app.errors import SaleError
from src.domain.order import OrderStatus
from src.interfaces.ierror_queue import IErrorQueue
from src.interfaces.iorder_service import IOrderService
from src.interfaces.iregistry import IRegistry
from src.interfaces.isale_service import ISaleService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletedUseCase:
    """Use case for completing sale orders."""

    order_services: IRegistry[IOrderService]
    sales_service: ISaleService
    error_queue: IErrorQueue
    notify_dir: Path

    def complete_sales(self) -> None:
        """Complete sales for all orders with status 'sale created'."""
        for order_provider, order_service in self.order_services.items():
            try:
                completed_sales = self.sales_service.get_completed_sales(order_provider)
                for _sale_id, remote_id in completed_sales:
                    if order := order_service.load_order(remote_id):
                        order_service.notify_completed_sale(order)
                        order_service.persist_order(order, OrderStatus.COMPLETED)
            except Exception as e:
                error = SaleError(
                    message=f"Error completing sales for provider {order_provider}: {e!s}",
                    order_id=None,
                )
                self.error_queue.put(error)
