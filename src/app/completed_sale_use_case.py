"""Completed sale orders use case.

This module handles the completion of sales orders across multiple order service providers.
It fetches completed sales from the sale service, loads the corresponding orders, notifies
providers of completion, and persists the updated order status. Errors at both the provider
and individual order level are caught and stored without interrupting processing of other orders.
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

    This use case:
    - Iterates through all registered order service providers
    - Retrieves completed sales for each provider
    - Loads and processes each completed order
    - Notifies providers of order completion
    - Persists the order status as COMPLETED
    - Handles errors gracefully at both provider and order levels without stopping processing

    Attributes:
        order_services: Registry of order service providers.
        sale_service: Service for retrieving and managing completed sales.
    """

    order_services: IRegistry[IOrderService]
    sale_service: ISaleService

    def execute(self) -> None:
        """Complete sales for all registered order service providers.

        For each provider:
        1. Retrieves the list of completed sales from the sale service
        2. For each completed sale:
           - Loads the corresponding order from the provider
           - Notifies the provider of order completion
           - Persists the order with COMPLETED status

        Errors are handled at two levels:
        - Order-level errors (load, notify, persist failures): Logged and stored; processing continues with next order
        - Provider-level errors (get_completed_sales failures): Logged and stored; processing continues with next provider

        All caught exceptions are stored in the ErrorStore singleton for later review.
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
