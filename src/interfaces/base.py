"""Core interface protocols for the application.

This module defines all the key Protocol interfaces used throughout the application
to enable dependency injection and testability. Protocols provide structural subtyping
(duck typing) without requiring explicit inheritance.

Interface categories:
- IUseCase: Orchestrates core business operations
- IRegistry: Generic container for managing service implementations
- IArtworkService: Retrieves artwork files for orders
- IOrderReader/IOrderStore/IOrderNotifier: Segmented order operations
- IArtworkServiceProvider: Selects artwork service based on order
- IOrderService: Composite interface combining all order operations
- ISaleService: Manages sales in the order management system
- IStockService: Handles stock transfer notifications

All interfaces use TYPE_CHECKING guards to avoid circular import issues with
the domain models they reference (Order, OrderStatus).
"""

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.domain import Order, OrderStatus


# ============================================================================
# Use Case Interface
# ============================================================================


class IUseCase(Protocol):
    """Protocol for a use case that orchestrates business logic.

    Use cases encapsulate specific business operations. Each use case
    performs a distinct workflow (e.g., process sales, handle stock transfers)
    and coordinates multiple services to accomplish its goal.

    Implementations should:
    - Fetch data from service providers
    - Perform domain logic and transformations
    - Store results and errors appropriately
    - Handle errors without stopping other operations
    """

    def execute(self) -> None:
        """Execute the use case workflow.

        Orchestrates the complete workflow for this use case. Implementations
        should handle all necessary operations and error conditions.

        Raises:
            May raise implementation-specific exceptions depending on the use case.
        """
        ...


# ============================================================================
# Registry Interface (Generic)
# ============================================================================


class IRegistry[T](Protocol):
    """Protocol for a thread-safe registry storing objects by name.

    A registry is a container for managing named instances of a type,
    commonly used for service registration and lookup. Implementations
    should be thread-safe for multi-threaded applications.

    Type parameter T represents the type of objects stored in the registry.
    Registries are typically used to store service implementations.

    Example:
        Registry[IArtworkService] stores various artwork service implementations
        indexed by provider name (e.g., 'spectrum', 'design-system').
    """

    def register(self, name: str, obj: T) -> None:
        """Register an object with a given name.

        Stores the object in the registry under the provided name.
        If an object with the same name already exists, it is replaced.

        Args:
            name: The name/key under which to register the object
            obj: The object to register
        """
        ...

    def get(self, name: str) -> T | None:
        """Retrieve an object by its name.

        Looks up the object registered under the given name.

        Args:
            name: The name/key of the object to retrieve

        Returns:
            The registered object, or None if not found
        """
        ...

    def unregister(self, name: str) -> None:
        """Unregister an object by its name.

        Removes the object registered under the given name from the registry.
        Safe to call even if the name is not registered (no-op).

        Args:
            name: The name/key of the object to unregister
        """
        ...

    def clear(self) -> None:
        """Clear all registered objects.

        Removes all objects from the registry, returning it to empty state.
        Typically used for testing or resetting the application state.
        """
        ...

    def items(self) -> Generator[tuple[str, T], None, None]:
        """Return all registered items as (name, object) pairs.

        Generates key-value pairs of all objects currently in the registry.
        Returns a snapshot of the registry at call time to support safe
        iteration even if the registry is modified concurrently.

        Yields:
            Tuple of (name, object) for each registered item
        """
        ...


# ============================================================================
# Artwork Service Interface
# ============================================================================


class IArtworkService(Protocol):
    """Protocol for artwork retrieval services.

    Artwork services are responsible for fetching design files (artwork)
    associated with orders. Different providers (e.g., Spectrum, design systems)
    may store and serve artwork differently, so this protocol defines the
    common interface for retrieving artwork regardless of provider.

    Implementations handle:
    - Connecting to provider systems
    - Locating artwork for specific orders
    - Downloading/retrieving files
    - File organization and caching
    """

    def get_artwork(self, order: "Order") -> list[Path]:
        """Get artwork data for the given order.

        Retrieves all artwork files associated with the order's line items.
        Returns high-level metadata list data for processing and manipulation.

        Args:
            order: The Order instance for which to retrieve artwork

        Returns:
            List of Path objects pointing to local artwork files

        Raises:
            May raise implementation-specific exceptions (network errors,
            file system errors, artwork not found, etc.)
        """
        ...


# ============================================================================
# Order Service Interfaces (Segregated)
# ============================================================================


class IOrderReader(Protocol):
    """Protocol for reading orders from a provider.

    Order readers fetch orders from order provider systems. They handle
    all connectivity and data parsing necessary to retrieve orders in
    a standardized format.

    Implementations handle:
    - Connecting to provider systems
    - Polling or monitoring for new orders
    - Parsing provider-specific order formats
    - Mapping to common Order domain model
    """

    def read_orders(self) -> Generator["Order", None, None]:
        """Generate orders from the provider.

        Retrieves orders from the provider system and yields them for processing.
        May read from directories, APIs, databases, or other sources depending
        on the provider implementation.

        Yields:
            Order instances ready for processing

        Raises:
            May raise implementation-specific exceptions (connection errors,
            parse errors, file system errors, etc.)
        """
        ...


class IOrderStore(Protocol):
    """Protocol for storing and retrieving orders.

    Order stores persist order data in a database or external system.
    This segregated interface focuses only on persistence operations,
    separate from reading new orders or notifying providers.

    Implementations handle:
    - Connecting to persistent storage
    - Converting domain models to storage format
    - Status tracking throughout order lifecycle
    - Retrieving previously stored orders
    """

    def persist_order(self, order: "Order", status: "OrderStatus") -> None:
        """Save the given order with its current status.

        Persists the order to storage with the provided status. This is called
        at key points in the order lifecycle (created, artwork processing,
        confirmed, completed, etc.).

        Args:
            order: The Order instance to persist
            status: The current OrderStatus of the order

        Raises:
            May raise implementation-specific exceptions (database errors,
            connection errors, etc.)
        """
        ...

    def load_order(self, remote_order_id: str) -> "Order":
        """Load an order by its remote ID.

        Retrieves a previously persisted order from storage by its external ID.

        Args:
            remote_order_id: The external order ID from the provider system

        Returns:
            The Order instance if found

        Raises:
            May raise implementation-specific exceptions (database errors,
            connection errors, etc.)
        """
        ...


class IOrderNotifier(Protocol):
    """Protocol for notifying order providers of completion.

    Order notifiers send completion notifications back to the order source
    system to indicate that a sale has been created successfully. Different
    providers have different notification systems (APIs, files, emails, etc.).

    Implementations handle:
    - Connecting to provider notification systems
    - Formatting notifications appropriately for the provider
    - Sending confirmations, replies, or status updates
    - Handling provider-specific confirmation requirements
    """

    def notify_completed_sale(self, order: "Order") -> None:
        """Notify the order provider that a sale order has been completed.

        Sends a completion notification back to the provider system to confirm
        that the order has been successfully processed and a sale created.
        The provider may use this to update their own systems or trigger
        fulfillment workflows.

        Args:
            order: The Order instance that has been completed

        Raises:
            May raise implementation-specific exceptions (connection errors,
            API errors, file system errors, etc.)
        """
        ...


class IArtworkServiceProvider(Protocol):
    """Protocol for selecting appropriate artwork service for an order.

    Different order providers may use different artwork providers/systems.
    This interface selects the correct artwork service based on the order's
    provider. Works with a registry of available artwork services.

    Implementations handle:
    - Matching orders to artwork service implementations
    - Providing fallback behavior if no service matches
    - Service registry management
    """

    def get_artwork_service(
        self, order: "Order", artwork_services: "IRegistry[IArtworkService]"
    ) -> IArtworkService | None:
        """Get the appropriate artwork service for the given order, or None if not found.

        Selects the correct artwork service from the registry based on the order's
        provider. The selection logic depends on the implementation (name matching,
        configuration mapping, etc.).

        Args:
            order: The Order for which to select an artwork service
            artwork_services: Registry of available IArtworkService implementations

        Returns:
            The appropriate IArtworkService for the order, or None if no suitable
            service is found in the registry
        """
        ...


class IOrderService(IOrderReader, IOrderStore, IOrderNotifier, IArtworkServiceProvider, Protocol):
    """Composite protocol combining all order-related operations.

    IOrderService aggregates multiple segregated interfaces into a single
    comprehensive interface for full-featured order services. This is useful
    for services that handle all aspects of order management.

    Combines:
    - IOrderReader: Reading orders from providers
    - IOrderStore: Persisting orders to storage
    - IOrderNotifier: Notifying providers of completion
    - IArtworkServiceProvider: Selecting artwork services

    Use specific interfaces (e.g., IOrderReader) when only certain operations
    are needed, reserving IOrderService for implementations that do everything.

    Example:
        >>> order_service: IOrderService = HarmanOrderService(...)
        >>> orders = list(order_service.read_orders())  # IOrderReader
        >>> order_service.persist_order(order, OrderStatus.CREATED)  # IOrderStore
        >>> order_service.notify_completed_sale(order)  # IOrderNotifier
    """

    ...


# ============================================================================
# Sale Service Interface
# ============================================================================


class ISaleService(Protocol):
    """Protocol for managing sales in the order management system.

    Sales services interface with the ERP/order management system to create
    and manage sales. Each order in the external system may need to have a
    corresponding sale created in the internal system. Sales services handle
    this translation and management.

    Implementations handle:
    - Connecting to the sales/order management system
    - Creating sales with order data
    - Verifying order integrity against sale data
    - Confirming sales after validation
    - Querying completed sales
    """

    def is_sale_created(self, order: "Order") -> bool:
        """Check if a sale has already been created for the given order.

        Determines whether a sale already exists in the system for this order,
        used to prevent duplicate sale creation.

        Args:
            order: The Order to check

        Returns:
            True if a sale exists for the order, False otherwise
        """
        ...

    def create_sale(self, order: "Order") -> int:
        """Create a sale for the given order and return its ID.

        Creates a new sale in the system based on the order data,
        mapping order details to sale format required by the system.

        Args:
            order: The Order for which to create a sale

        Returns:
            The ID of the newly created sale

        Raises:
            May raise implementation-specific exceptions (API errors,
            data validation errors, etc.)
        """
        ...

    def confirm_sale(self, order: "Order") -> None:
        """Confirm the sale for the given order.

        Marks the sale as confirmed/approved in the system, typically after
        artwork processing and validation is complete.

        Args:
            order: The Order whose sale should be confirmed

        Raises:
            May raise implementation-specific exceptions (API errors,
            invalid state errors, etc.)
        """
        ...

    def has_expected_order_lines(self, order: "Order") -> bool:
        """Verify that the sale has the same order line quantities as the local order.

        Validates that the created sale matches the original order specification,
        checking that line items and quantities are consistent.

        Args:
            order: The Order to verify

        Returns:
            True if the sale has matching order lines, False otherwise
        """
        ...

    def update_contact(self, order: "Order") -> None:
        """Update the contact information for the given order.

        Updates contact details (billing/shipping address, email, phone) in
        the sale to match the latest information in the order.

        Args:
            order: The Order whose contact information should be updated

        Raises:
            May raise implementation-specific exceptions (API errors, etc.)
        """
        ...

    def update_delivery_instructions(self, order: "Order") -> None:
        """Update the delivery instructions for the given order.

        Updates delivery instructions in the sale to match the latest information
        in the order.

        Args:
            order: The Order whose delivery instructions should be updated

        Raises:
            May raise implementation-specific exceptions (API errors, etc.)
        """
        ...

    def get_completed_sales(self, order_provider: str) -> list[tuple[int, str]]:
        """Get a list of completed sales.

        Retrieves sales that have been completed and shipped, optionally
        filtered by the order provider.

        Args:
            order_provider: Filter completed sales for this order provider

        Returns:
            List of (sale_id, remote_order_id) tuples for completed sales
        """
        ...

    def get_shipping_info(self, order: "Order") -> list[dict[str, Any]]:
        """Get the shipping information for the given order.

        Retrieves shipment tracking and delivery details for the order
        from the sales system.

        Args:
            order: The Order for which to retrieve shipping information

        Returns:
            List of dictionaries containing shipping information
        """
        ...

    def get_serials_by_line_item(self, order: "Order") -> dict[str, list[str]]:
        """Get the serial numbers for the given order by line item.

        Retrieves product serial numbers for tracking and fulfillment,
        organized by line item.

        Args:
            order: The Order for which to retrieve serial numbers

        Returns:
            Dictionary mapping line item IDs to lists of serial numbers
        """
        ...


# ============================================================================
# Stock Service Interface
# ============================================================================


class IStockService(Protocol):
    """Protocol for handling stock transfer notifications.

    Stock services manage inbound stock transfer requests from suppliers or
    warehouse systems. They read transfer notifications and send confirmations
    back to the supplier system.

    Implementations handle:
    - Monitoring for stock transfer notifications
    - Parsing transfer data (delivery numbers, items, quantities)
    - Sending transfer confirmations to the supplier
    - File organization and archival
    """

    def read_stock_transfers(self) -> Generator[dict[str, Any], None, None]:
        """Read stock transfer requests.

        Monitors for and reads inbound stock transfer notifications from
        the supplier/warehouse system.

        Yields:
            Dictionary containing transfer data (delivery number, items, quantities, etc.)

        Raises:
            May raise implementation-specific exceptions (file system errors,
            parse errors, etc.)
        """
        ...

    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Reply to stock transfer requests.

        Sends a confirmation/acknowledgment back to the supplier/warehouse system
        for the given stock transfer. May create reply files, send emails, or
        post to supplier APIs depending on the implementation.

        Args:
            transfer_data: Dictionary containing the transfer data to acknowledge

        Raises:
            May raise implementation-specific exceptions (file system errors,
            API errors, email errors, etc.)
        """
        ...
