"""Interface protocols for the application.

All interfaces are centralized in base.py for easy maintenance and import.
"""

from src.interfaces.base import (
    IArtworkService,
    IArtworkServiceProvider,
    IOrderNotifier,
    IOrderReader,
    IOrderService,
    IOrderStore,
    IRegistry,
    ISaleService,
    IStockService,
    IUseCase,
)

__all__ = [
    "IArtworkService",
    "IArtworkServiceProvider",
    "IOrderNotifier",
    "IOrderReader",
    "IOrderService",
    "IOrderStore",
    "IRegistry",
    "ISaleService",
    "IStockService",
    "IUseCase",
]
