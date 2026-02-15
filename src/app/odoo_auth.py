"""Odoo authentication module."""

from dataclasses import dataclass
from typing import Self

from src.settings import Settings


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooAuth:
    """Odoo authentication data."""

    database: str
    user_id: int
    password: str

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """Create an OdooAuth instance from settings."""
        return cls(
            database=settings.odoo_database,
            user_id=settings.odoo_rpc_user_id,
            password=settings.odoo_rpc_password,
        )
