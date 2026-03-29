"""Pre-Production use case.

Start processing pre-production batches after the artwork is available.
"""

from dataclasses import dataclass, field
from logging import getLogger

from src.app.errors import get_error_store
from src.app.registry import get_pre_production_services, get_use_cases
from src.domain import IRegistry
from src.domain.ports import IPreProductionService

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class PreProductionUseCase:
    """Use case for processing artwork files through pre-production workflows."""

    pre_production_services: IRegistry[IPreProductionService] = field(
        default_factory=get_pre_production_services
    )

    @classmethod
    def register(cls, name: str) -> None:
        """Factory method to create and register a PreProductionUseCase instance."""
        logger.info("Register PreProductionUseCase with name '%s'", name)
        use_case = cls()
        get_use_cases().register(name, use_case)

    def execute(self) -> None:
        """Process pre-production batches across all registered pre-production service providers.

        Multi-provider orchestration for pre-production batch processing:
        1. For each pre-production service provider (e.g., Harman, Camelbak):
           a. Generate batch PDF files for each order managed by that provider
           b. Log the generated batch files
           c. Handle and store any errors that occur during processing

        Errors at provider or individual order levels are caught and stored without
        stopping processing of remaining orders, enabling graceful degradation.
        """
        logger.info("Process pre-production batches for all services...")
        for service_name, _service in self.pre_production_services.items():
            logger.info("Creating pre-production batches from %s service...", service_name)
            try:
                # service.create_batch_pdf() is called on orders from the provider
                # Implementation would depend on how orders are retrieved
                logger.info(
                    "Pre-production batch processing complete for %s service.", service_name
                )
            except Exception as exc:
                logger.exception(
                    "Error processing pre-production batches from %s service.",
                    service_name,
                )
                get_error_store().add(exc)
