"""Completed sale orders use case.

Handle completion of sales orders across multiple service providers.
"""

from dataclasses import dataclass, field
from logging import getLogger

from src.app.errors import ErrorStore, SaleError, get_error_store
from src.app.registry import get_order_services, get_sale_services, get_use_cases
from src.domain import IOrderService, IRegistry, ISaleService, OrderStatus

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletedSaleUseCase:
    """Use case for completing sale orders across multiple order service providers.

    Retrieves completed sales, loads orders, notifies providers, and persists status.
    Handles errors per-provider and per-order without stopping processing.
    """

    order_services: IRegistry[IOrderService] = field(default_factory=get_order_services)
    sale_services: IRegistry[ISaleService] = field(default_factory=get_sale_services)

    @classmethod
    def register(cls, name: str) -> None:
        """Factory method to create and register a CompletedSaleUseCase instance."""
        use_case = cls()
        get_use_cases().register(name, use_case)

    def execute(self) -> None:
        """Complete sales for all registered order service providers.

        Handle errors at provider and order levels without stopping processing.
        """
        logger.info("Complete sales for all order services...")
        error_store: ErrorStore = get_error_store()
        for order_provider, order_service in self.order_services.items():
            try:
                logger.info("Complete sales for %s service...", order_provider)
                for sale_service_name, sale_service in self.sale_services.items():
                    logger.info(
                        "Check completed sales for %s service in %s sale service...",
                        order_provider,
                        sale_service_name,
                    )
                    completed_sales = sale_service.search_completed_sales(order_provider)
                    for _sale_id, remote_order_id in completed_sales:
                        try:
                            if order := order_service.load_order(remote_order_id):
                                logger.debug("Notify completed sale for order %s", remote_order_id)
                                notify_data = order_service.get_notify_data(order, sale_service)
                                order_service.notify_completed_sale(order, notify_data)
                                sale_service.mark_sale_notified(_sale_id)
                                order_service.persist_order(order, OrderStatus.COMPLETED)
                            else:
                                raise SaleError(
                                    message=f"Order with remote ID {remote_order_id} not found",
                                    order_id=remote_order_id,
                                )
                        except Exception as exc:
                            logger.exception(
                                "Failed to complete sale for order %s", remote_order_id
                            )
                            error_store.add(exc)
            except Exception as exc:
                logger.exception("Failed to complete sales for %s service", order_provider)
                error_store.add(exc)
