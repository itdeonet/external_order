"""Odoo RPC authentication credentials and factory.

Provides an immutable credential container and a cached factory built from
application configuration.
"""

from dataclasses import dataclass, field

from src.config import get_config


@dataclass(frozen=True, slots=True, kw_only=True)
class OdooAuth:
    """Immutable container for Odoo RPC credentials.

    Holds `database`, `user_id`, and `password`. Fields are validated on init.
    """

    database: str = field(default_factory=lambda: get_config().odoo_database)
    user_id: int = field(default_factory=lambda: get_config().odoo_rpc_user_id)
    password: str = field(default_factory=lambda: get_config().odoo_rpc_password)

    def __post_init__(self) -> None:
        """Validate credentials and raise ValueError on invalid values."""
        if not (self.database and isinstance(self.database, str) and self.database.strip()):
            raise ValueError("Database cannot be empty.")
        if self.user_id <= 0:
            raise ValueError("User ID must be a positive integer.")
        if not (self.password and isinstance(self.password, str) and self.password.strip()):
            raise ValueError("Password cannot be empty.")
