"""Settings for the application."""

from dataclasses import dataclass, field
from functools import cache
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Settings for the application."""

    work_dir: Path = Path.home() / "projects_data" / "external_order"
    json_orders_dir: Path = field(default=Path.home(), init=False)

    # Harman settings
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "Harman INSDES"
    harman_shipment_type: str = "harman%"
    harman_workdays_for_delivery: int = 2
    harman_input_orders_dir: Path = field(default=Path.home(), init=False)

    # Odoo settings
    odoo_base_url: str = os.getenv("ODOO_BASE_URL", "")
    odoo_database: str = os.getenv("ODOO_DATABASE", "")
    odoo_rpc_user_id: int = int(os.getenv("ODOO_USER_ID", "0"))
    odoo_rpc_password: str = os.getenv("ODOO_PASSWORD", "")

    def __post_init__(self):
        """Initialize settings."""
        object.__setattr__(self, "harman_input_orders_dir", self.work_dir / "in" / "insdes")
        object.__setattr__(self, "json_orders_dir", self.work_dir / "orders")

        self.harman_input_orders_dir.mkdir(parents=True, exist_ok=True)
        self.json_orders_dir.mkdir(parents=True, exist_ok=True)


@cache
def get_settings() -> Settings:
    """Get the application settings."""
    return Settings()
