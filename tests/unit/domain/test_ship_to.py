"""Unit tests for the ShipTo domain class."""

import pytest

from src.domain.ship_to import ShipTo


class TestShipToInstantiation:
    """Tests for basic ShipTo instantiation."""

    @pytest.fixture
    def valid_ship_to_data(self):
        """Provide valid ShipTo initialization data."""
        return {
            "remote_customer_id": "CUST12345",
            "company_name": "Acme Corp",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-123-4567",
            "street1": "123 Main St",
            "street2": "Suite 100",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country_code": "US",
        }

    def test_instantiation_with_all_fields(self, valid_ship_to_data):
        """Test creating a ShipTo with all fields."""
        ship_to = ShipTo(**valid_ship_to_data)

        assert ship_to.remote_customer_id == "CUST12345"
        assert ship_to.company_name == "Acme Corp"
        assert ship_to.contact_name == "John Doe"
        assert ship_to.email == "john@example.com"
        assert ship_to.phone == "+1-555-123-4567"
        assert ship_to.street1 == "123 Main St"
        assert ship_to.street2 == "Suite 100"
        assert ship_to.city == "Springfield"
        assert ship_to.state == "IL"
        assert ship_to.postal_code == "62701"
        assert ship_to.country_code == "US"

    def test_instantiation_with_minimal_fields(self):
        """Test creating a ShipTo with only required fields."""
        ship_to = ShipTo(
            remote_customer_id="CUST123",
            contact_name="Jane Smith",
            email="jane@example.com",
            phone="555-0123",
            street1="456 Oak Ave",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )

        assert ship_to.remote_customer_id == "CUST123"
        assert ship_to.company_name == ""
        assert ship_to.contact_name == "Jane Smith"
        assert ship_to.street2 == ""
        assert ship_to.state == ""


class TestShipToRemoteCustomerIDValidation:
    """Tests for remote_customer_id field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_remote_customer_id_required(self, minimal_ship_to_data):
        """Test that remote_customer_id is required."""
        minimal_ship_to_data.pop("contact_name")
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_remote_customer_id_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty remote_customer_id raises ValueError."""
        with pytest.raises(ValueError, match="Remote customer ID must be a non-empty string"):
            ShipTo(remote_customer_id="", **minimal_ship_to_data)

    def test_remote_customer_id_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only remote_customer_id raises ValueError."""
        with pytest.raises(ValueError, match="Remote customer ID must be a non-empty string"):
            ShipTo(remote_customer_id="   ", **minimal_ship_to_data)

    def test_remote_customer_id_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around remote_customer_id is stripped."""
        ship_to = ShipTo(remote_customer_id="  CUST123  ", **minimal_ship_to_data)
        assert ship_to.remote_customer_id == "CUST123"


class TestShipToCompanyNameHandling:
    """Tests for company_name field handling."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_company_name_optional_defaults_to_empty(self, minimal_ship_to_data):
        """Test that company_name defaults to empty string."""
        ship_to = ShipTo(**minimal_ship_to_data)
        assert ship_to.company_name == ""

    def test_company_name_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around company_name is stripped."""
        ship_to = ShipTo(company_name="  Acme Corp  ", **minimal_ship_to_data)
        assert ship_to.company_name == "Acme Corp"

    def test_company_name_whitespace_only_becomes_empty(self, minimal_ship_to_data):
        """Test that whitespace-only company_name becomes empty string."""
        ship_to = ShipTo(company_name="   ", **minimal_ship_to_data)
        assert ship_to.company_name == ""


class TestShipToContactNameValidation:
    """Tests for contact_name field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_contact_name_required(self, minimal_ship_to_data):
        """Test that contact_name is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_contact_name_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty contact_name raises ValueError."""
        with pytest.raises(ValueError, match="Contact name must be a non-empty string"):
            ShipTo(contact_name="", **minimal_ship_to_data)

    def test_contact_name_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only contact_name raises ValueError."""
        with pytest.raises(ValueError, match="Contact name must be a non-empty string"):
            ShipTo(contact_name="   ", **minimal_ship_to_data)

    def test_contact_name_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around contact_name is stripped."""
        ship_to = ShipTo(contact_name="  John Doe  ", **minimal_ship_to_data)
        assert ship_to.contact_name == "John Doe"


class TestShipToEmailValidation:
    """Tests for email field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_email_required(self, minimal_ship_to_data):
        """Test that email is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_email_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty email raises ValueError."""
        with pytest.raises(ValueError, match="Email must be a non-empty string"):
            ShipTo(email="", **minimal_ship_to_data)

    def test_email_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only email raises ValueError."""
        with pytest.raises(ValueError, match="Email must be a non-empty string"):
            ShipTo(email="   ", **minimal_ship_to_data)

    def test_email_missing_at_sign_raises_error(self, minimal_ship_to_data):
        """Test that email without @ raises ValueError."""
        with pytest.raises(ValueError, match="Email must be a valid email address"):
            ShipTo(email="invalid.email", **minimal_ship_to_data)

    def test_email_missing_dot_after_at_raises_error(self, minimal_ship_to_data):
        """Test that email without dot in domain raises ValueError."""
        with pytest.raises(ValueError, match="Email must be a valid email address"):
            ShipTo(email="user@nodomain", **minimal_ship_to_data)

    def test_email_gets_stripped_and_lowercased(self, minimal_ship_to_data):
        """Test that whitespace is stripped and email is lowercased."""
        ship_to = ShipTo(email="  John@Example.COM  ", **minimal_ship_to_data)
        assert ship_to.email == "john@example.com"

    def test_email_valid_formats(self, minimal_ship_to_data):
        """Test various valid email formats."""
        valid_emails = [
            "user@example.com",
            "john.doe@company.co.uk",
            "test+tag@domain.org",
        ]
        for email in valid_emails:
            ship_to = ShipTo(email=email, **minimal_ship_to_data)
            assert ship_to.email == email.lower()


class TestShipToPhoneValidation:
    """Tests for phone field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_phone_required(self, minimal_ship_to_data):
        """Test that phone is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_phone_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty phone raises ValueError."""
        with pytest.raises(ValueError, match="Phone must be a non-empty string"):
            ShipTo(phone="", **minimal_ship_to_data)

    def test_phone_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only phone raises ValueError."""
        with pytest.raises(ValueError, match="Phone must be a non-empty string"):
            ShipTo(phone="   ", **minimal_ship_to_data)

    def test_phone_invalid_characters_raises_error(self, minimal_ship_to_data):
        """Test that phone with invalid characters raises ValueError."""
        with pytest.raises(ValueError, match="Phone must contain only digits and valid characters"):
            ShipTo(phone="555-0123abc", **minimal_ship_to_data)

    def test_phone_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around phone is stripped."""
        ship_to = ShipTo(phone="  555-0123  ", **minimal_ship_to_data)
        assert ship_to.phone == "555-0123"

    def test_phone_valid_formats(self, minimal_ship_to_data):
        """Test various valid phone formats."""
        valid_phones = [
            "555-0123",
            "+1-555-0123",
            "(555) 0123",
            "555 0123",
            "5550123",
            "+1 555 0123",
        ]
        for phone in valid_phones:
            ship_to = ShipTo(phone=phone, **minimal_ship_to_data)
            assert ship_to.phone == phone.strip()


class TestShipToStreetValidation:
    """Tests for street fields validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_street1_required(self, minimal_ship_to_data):
        """Test that street1 is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_street1_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty street1 raises ValueError."""
        with pytest.raises(ValueError, match="Street1 must be a non-empty string"):
            ShipTo(street1="", **minimal_ship_to_data)

    def test_street1_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only street1 raises ValueError."""
        with pytest.raises(ValueError, match="Street1 must be a non-empty string"):
            ShipTo(street1="   ", **minimal_ship_to_data)

    def test_street1_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around street1 is stripped."""
        ship_to = ShipTo(street1="  123 Main St  ", **minimal_ship_to_data)
        assert ship_to.street1 == "123 Main St"

    def test_street2_optional_defaults_to_empty(self, minimal_ship_to_data):
        """Test that street2 defaults to empty string."""
        ship_to = ShipTo(street1="123 Main St", **minimal_ship_to_data)
        assert ship_to.street2 == ""

    def test_street2_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around street2 is stripped."""
        ship_to = ShipTo(street1="123 Main St", street2="  Suite 100  ", **minimal_ship_to_data)
        assert ship_to.street2 == "Suite 100"

    def test_street2_whitespace_only_becomes_empty(self, minimal_ship_to_data):
        """Test that whitespace-only street2 becomes empty string."""
        ship_to = ShipTo(street1="123 Main St", street2="   ", **minimal_ship_to_data)
        assert ship_to.street2 == ""


class TestShipToCityValidation:
    """Tests for city field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_city_required(self, minimal_ship_to_data):
        """Test that city is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_city_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty city raises ValueError."""
        with pytest.raises(ValueError, match="City must be a non-empty string"):
            ShipTo(city="", **minimal_ship_to_data)

    def test_city_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only city raises ValueError."""
        with pytest.raises(ValueError, match="City must be a non-empty string"):
            ShipTo(city="   ", **minimal_ship_to_data)

    def test_city_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around city is stripped."""
        ship_to = ShipTo(city="  Chicago  ", **minimal_ship_to_data)
        assert ship_to.city == "Chicago"


class TestShipToStateHandling:
    """Tests for state field handling."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_state_optional_defaults_to_empty(self, minimal_ship_to_data):
        """Test that state defaults to empty string."""
        ship_to = ShipTo(**minimal_ship_to_data)
        assert ship_to.state == ""

    def test_state_gets_stripped(self, minimal_ship_to_data):
        """Test that whitespace around state is stripped."""
        ship_to = ShipTo(state="  IL  ", **minimal_ship_to_data)
        assert ship_to.state == "IL"

    def test_state_whitespace_only_becomes_empty(self, minimal_ship_to_data):
        """Test that whitespace-only state becomes empty string."""
        ship_to = ShipTo(state="   ", **minimal_ship_to_data)
        assert ship_to.state == ""


class TestShipToPostalCodeValidation:
    """Tests for postal_code field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "country_code": "US",
        }

    def test_postal_code_required(self, minimal_ship_to_data):
        """Test that postal_code is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_postal_code_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty postal_code raises ValueError."""
        with pytest.raises(ValueError, match="Postal code must be a non-empty string"):
            ShipTo(postal_code="", **minimal_ship_to_data)

    def test_postal_code_whitespace_only_raises_error(self, minimal_ship_to_data):
        """Test that whitespace-only postal_code raises ValueError."""
        with pytest.raises(ValueError, match="Postal code must be a non-empty string"):
            ShipTo(postal_code="   ", **minimal_ship_to_data)

    def test_postal_code_gets_stripped_and_uppercased(self, minimal_ship_to_data):
        """Test that postal_code is stripped and uppercased."""
        ship_to = ShipTo(postal_code="  60601  ", **minimal_ship_to_data)
        assert ship_to.postal_code == "60601"

    def test_postal_code_lowercase_gets_uppercased(self, minimal_ship_to_data):
        """Test that lowercase postal codes are uppercased."""
        ship_to = ShipTo(postal_code="m5v3a8", **minimal_ship_to_data)
        assert ship_to.postal_code == "M5V3A8"


class TestShipToCountryCodeValidation:
    """Tests for country_code field validation."""

    @pytest.fixture
    def minimal_ship_to_data(self):
        """Provide minimal valid ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
        }

    def test_country_code_required(self, minimal_ship_to_data):
        """Test that country_code is required."""
        with pytest.raises(TypeError):
            ShipTo(**minimal_ship_to_data)

    def test_country_code_empty_raises_error(self, minimal_ship_to_data):
        """Test that empty country_code raises ValueError."""
        with pytest.raises(ValueError, match="Country code must be a 2-letter ISO code"):
            ShipTo(country_code="", **minimal_ship_to_data)

    def test_country_code_single_letter_raises_error(self, minimal_ship_to_data):
        """Test that 1-letter country_code raises ValueError."""
        with pytest.raises(ValueError, match="Country code must be a 2-letter ISO code"):
            ShipTo(country_code="U", **minimal_ship_to_data)

    def test_country_code_three_letters_raises_error(self, minimal_ship_to_data):
        """Test that 3-letter country_code raises ValueError."""
        with pytest.raises(ValueError, match="Country code must be a 2-letter ISO code"):
            ShipTo(country_code="USA", **minimal_ship_to_data)

    def test_country_code_gets_stripped_and_uppercased(self, minimal_ship_to_data):
        """Test that country_code is stripped and uppercased."""
        ship_to = ShipTo(country_code="  ca  ", **minimal_ship_to_data)
        assert ship_to.country_code == "CA"

    def test_country_code_uppercase_preserved(self, minimal_ship_to_data):
        """Test that uppercase country codes are preserved."""
        ship_to = ShipTo(country_code="US", **minimal_ship_to_data)
        assert ship_to.country_code == "US"


class TestShipToImmutability:
    """Tests for ShipTo immutability (frozen dataclass)."""

    @pytest.fixture
    def ship_to(self):
        """Provide a ShipTo instance."""
        return ShipTo(
            remote_customer_id="CUST123",
            contact_name="John Doe",
            email="john@example.com",
            phone="555-0123",
            street1="123 Main St",
            city="Chicago",
            postal_code="60601",
            country_code="US",
        )

    def test_cannot_modify_id(self, ship_to):
        """Test that id cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            ship_to.id = "new-id"

    def test_cannot_modify_contact_name(self, ship_to):
        """Test that contact_name cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            ship_to.contact_name = "Jane Doe"

    def test_cannot_modify_email(self, ship_to):
        """Test that email cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            ship_to.email = "jane@example.com"

    def test_cannot_modify_phone(self, ship_to):
        """Test that phone cannot be modified."""
        with pytest.raises((AttributeError, TypeError)):
            ship_to.phone = "555-9999"

    def test_cannot_modify_any_field(self, ship_to):
        """Test that no field can be modified."""
        with pytest.raises((AttributeError, TypeError)):
            ship_to.street1 = "456 Oak Ave"


class TestShipToEquality:
    """Tests for ShipTo equality comparison."""

    @pytest.fixture
    def ship_to_data(self):
        """Provide standard ShipTo data."""
        return {
            "remote_customer_id": "CUST123",
            "contact_name": "John Doe",
            "email": "john@example.com",
            "phone": "555-0123",
            "street1": "123 Main St",
            "city": "Chicago",
            "postal_code": "60601",
            "country_code": "US",
        }

    def test_different_instances_same_data_are_equal(self, ship_to_data):
        """Test that two instances with same data are equal."""
        ship_to1 = ShipTo(**ship_to_data)
        ship_to2 = ShipTo(**ship_to_data)
        assert ship_to1 == ship_to2
