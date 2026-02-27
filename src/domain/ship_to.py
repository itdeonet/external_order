"""A shipping address for an order."""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class ShipTo:
    """A shipping address for an order."""

    id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)
    remote_customer_id: str
    company_name: str = ""
    contact_name: str
    email: str
    phone: str
    street1: str
    street2: str = ""
    city: str
    state: str = ""
    postal_code: str
    country_code: str

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if not (isinstance(self.remote_customer_id, str) and self.remote_customer_id.strip()):
            raise ValueError("Remote customer ID must be a non-empty string")
        object.__setattr__(self, "remote_customer_id", self.remote_customer_id.strip())

        if isinstance(self.company_name, str):
            object.__setattr__(self, "company_name", self.company_name.strip())
        else:
            object.__setattr__(self, "company_name", "")

        if not (isinstance(self.contact_name, str) and self.contact_name.strip()):
            raise ValueError("Contact name must be a non-empty string")
        object.__setattr__(self, "contact_name", self.contact_name.strip())

        if not (isinstance(self.email, str) and self.email.strip()):
            raise ValueError("Email must be a non-empty string")
        if not ("@" in self.email and "." in self.email.split("@")[-1]):
            raise ValueError("Email must be a valid email address")
        object.__setattr__(self, "email", self.email.strip().lower())

        if not (isinstance(self.phone, str) and self.phone.strip()):
            raise ValueError("Phone must be a non-empty string")
        if not all(c.isdigit() or c in "+-() " for c in self.phone):
            raise ValueError("Phone must contain only digits and valid characters")
        object.__setattr__(self, "phone", self.phone.strip())

        if not (isinstance(self.street1, str) and self.street1.strip()):
            raise ValueError("Street1 must be a non-empty string")
        object.__setattr__(self, "street1", self.street1.strip())

        if isinstance(self.street2, str):
            object.__setattr__(self, "street2", self.street2.strip())
        else:
            object.__setattr__(self, "street2", "")

        if not (isinstance(self.city, str) and self.city.strip()):
            raise ValueError("City must be a non-empty string")
        object.__setattr__(self, "city", self.city.strip())

        if not (isinstance(self.state, str)):
            object.__setattr__(self, "state", "")
        object.__setattr__(self, "state", self.state.strip())

        if not (isinstance(self.postal_code, str) and self.postal_code.strip()):
            raise ValueError("Postal code must be a non-empty string")
        object.__setattr__(self, "postal_code", self.postal_code.strip().upper())

        if not (isinstance(self.country_code, str) and len(self.country_code.strip()) == 2):
            raise ValueError("Country code must be a 2-letter ISO code")
        object.__setattr__(self, "country_code", self.country_code.strip().upper())
