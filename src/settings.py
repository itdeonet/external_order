"""Settings for the application."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Settings for the application."""

    # Harman settings
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "Harman INSDES"
    harman_shipment_type: str = "harman%"

    work_dir: Path = Path.home() / "external_order"


@cache
def get_settings() -> Settings:
    """Get the application settings."""
    return Settings()
