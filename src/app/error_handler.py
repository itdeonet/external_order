"""Error handling utilities for use cases."""

from logging import getLogger

from src.app.errors import SaleError
from src.interfaces import IErrorQueue

logger = getLogger(__name__)


class ErrorHandler:
    """Utility class for handling errors in use cases."""

    def __init__(self, error_queue: IErrorQueue) -> None:
        """Initialize the error handler with an error queue.

        Args:
            error_queue: The error queue to put exceptions into.
        """
        self.error_queue = error_queue

    def handle_order_error(
        self,
        exc: Exception,
        order_id: str,
        service_name: str,
        log_message: str = "Error processing order",
    ) -> None:
        """Handle an error that occurred while processing an order.

        Args:
            exc: The exception that occurred.
            order_id: The ID of the order being processed.
            service_name: The name of the service processing the order.
            log_message: The message to log (without order/service details).
        """
        logger.exception(
            "%s %s from %s service",
            log_message,
            order_id,
            service_name,
        )
        if isinstance(exc, SaleError):
            self.error_queue.put(exc)
        else:
            self.error_queue.put(
                SaleError(
                    message=f"{exc!s} (Service: {service_name})",
                    order_id=order_id,
                )
            )

    def handle_provider_error(
        self,
        exc: Exception,
        provider_name: str,
        order_id: str | None = None,
        log_message: str = "Error",
    ) -> None:
        """Handle an error that occurred while processing a provider.

        Args:
            exc: The exception that occurred.
            provider_name: The name of the provider.
            order_id: Optional ID of the order being processed (can be None for provider-level errors).
            log_message: The message to log.
        """
        if order_id:
            logger.exception("%s for order %s", log_message, order_id)
        else:
            logger.exception("%s for provider %s: %s", log_message, provider_name, exc)

        if isinstance(exc, SaleError):
            self.error_queue.put(exc)
        else:
            self.error_queue.put(
                SaleError(
                    message=f"{exc!s} (Provider: {provider_name})",
                    order_id=order_id,
                )
            )
