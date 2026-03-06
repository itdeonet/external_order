# Deonet External Order Synchronization

A modular order synchronization system that imports orders from external providers, creates sales in Odoo, manages artwork workflows, and handles stock transfers. Built with Python 3.12+ using clean architecture principles.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Architecture](#architecture)
- [Setup and Installation](#setup-and-installation)
- [Configuration](#configuration)
- [Domain Entities](#domain-entities)
- [Adding New Services](#adding-new-services)
- [Testing](#testing)
- [Error Handling](#error-handling)
- [Development Workflow](#development-workflow)
- [Dependencies](#dependencies)

## Overview

This application orchestrates a multi-step workflow for processing external orders:

1. **Read Orders** - Import order data from external providers (currently Harman, extensible to others)
2. **Create Sales** - Create corresponding sales in Odoo ERP system
3. **Manage Artwork** - Fetch and manage product artwork from external services (Spectrum)
4. **Confirm Sales** - Complete the sales workflow in Odoo
5. **Stock Transfers** - Handle inventory movements between warehouse systems
6. **Notifications** - Send delivery notifications (EDIFACT format)

The system is designed as a **pluggable service architecture** where new order providers, artwork services, and stock systems can be added without modifying core logic.

## File Structure

```
deonet-external-order/
├── src/                           # Application source code
│   ├── app/                       # Application layer (use cases)
│   │   ├── completed_sale_use_case.py      # Process completed sales
│   │   ├── new_sale_use_case.py            # Create new sales workflow
│   │   ├── stock_transfer_use_case.py      # Handle stock transfers
│   │   ├── odoo_auth.py                    # Odoo authentication
│   │   ├── registry.py                     # Service registry (plugin pattern)
│   │   └── errors.py                       # Custom exception types & ErrorStore
│   │
│   ├── domain/                    # Domain layer (business entities)
│   │   ├── order.py               # Order aggregate root
│   │   ├── line_item.py           # Order line item
│   │   ├── ship_to.py             # Shipping address
│   │   ├── artwork.py             # Artwork metadata
│   │   └── validators.py          # Domain validation rules
│   │
│   ├── services/                  # Infrastructure layer (external integrations)
│   │   ├── harman_order_service.py         # Harman order provider
│   │   ├── harman_stock_service.py         # Harman stock transfers
│   │   ├── odoo_sale_service.py            # Odoo ERP integration
│   │   ├── spectrum_artwork_service.py     # Spectrum artwork provider
│   │   └── render_service.py               # Jinja2 template rendering
│   │
│   ├── interfaces/                # Interface contracts (protocols)
│   │   ├── base.py                # All interface definitions
│   │   └── __init__.py            # Interface exports
│   │
│   ├── templates/                 # Jinja2 templates
│   │   ├── desadvd96a.j2          # EDIFACT D96A delivery notification
│   │   └── desadvd99a.j2          # EDIFACT D99A delivery notification
│   │
│   ├── config.py                  # Configuration management
│   └── main.py                    # Application entry point
│
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests (100+ tests)
│   │   ├── app/                   # Use case tests
│   │   ├── domain/                # Entity and validator tests
│   │   └── services/              # Service integration tests
│   │
│   └── integration/               # Integration tests
│       └── test_main.py           # Main setup tests
│
├── pyproject.toml                 # Project configuration & dependencies
├── README.md                      # This file
└── .env.example                   # Example environment variables
```

**Key Directories:**

- **`src/app/`** - Use cases & application orchestration (no business logic, pure coordination)
- **`src/domain/`** - Pure business logic & validation rules (framework-agnostic)
- **`src/services/`** - External system integrations & HTTP clients
- **`src/interfaces/`** - Protocol definitions (TypeScript-like interfaces for Python)

## Architecture

### High-Level Data Flow

```
External Order Provider (Harman)
        ↓
    Read Orders [IOrderReader]
        ↓
  Create Sale in Odoo [ISaleService]
        ↓
  Get Artwork [IArtworkService] ← Spectrum Artwork Service
        ↓
  Confirm Sale in Odoo
        ↓
  Notify Provider [IOrderNotifier] ← EDIFACT D96A/D99A
        ↓
  Handle Stock Transfers [IStockService]
```

### Core Design Patterns

#### 1. **Service Registry (Plugin Architecture)**

Services are registered at runtime, allowing new providers to be plugged in without code changes:

```python
# In main.py
order_services: IRegistry[IOrderService] = Registry[IOrderService]()
order_services.register("Harman", HarmanOrderService.from_config(config))
order_services.register("MyNewProvider", MyNewOrderService.from_config(config))

# In use cases, iterate over all registered services
for order_service_name, order_service in order_services.items():
    for order in order_service.read_orders():
        # Process order
```

#### 2. **Protocol-Based Interfaces**

Services implement Python Protocol interfaces (like TypeScript interfaces). Each protocol defines a specific capability:

- `IOrderReader` - Read orders from a provider
- `IOrderStore` - Persist order state
- `IOrderNotifier` - Send notifications
- `IArtworkServiceProvider` - Select artwork service for order
- `IOrderService` - Full-featured order provider (combines all above)

Note: Error handling uses a singleton `ErrorStore` class, not an interface, to centralize error collection across all operations.

#### 3. **Separation of Concerns**

- **App Layer** - Orchestration & workflow (use cases)
- **Domain Layer** - Business rules & validation (order, line items, etc.)
- **Service Layer** - External system integration (Odoo, Harman, Spectrum)
- **Interface Layer** - Contracts between layers (protocols)

#### 4. **Error Store Pattern**

Instead of throwing exceptions up the call stack, errors are collected in a singleton ErrorStore for centralized handling:

```python
from src.app.errors import ErrorStore

# Get singleton instance
error_store = ErrorStore()

for order in order_service.read_orders():
    try:
        # Process order
    except Exception as exc:
        error_store.add(exc)
        logger.error(f"Error processing order: {exc!s}")

# Summarize all errors at the end
if error_store.has_errors():
    logger.error(error_store.summarize())
```

### Use Cases (Application Workflows)

#### **NewSaleUseCase**
Workflow: Read Orders → Create/Update Sales → Get Artwork → Confirm Sales

```python
NewSaleUseCase.execute():
  for each order_service:
    for each order:
      1. Persist order as NEW
      2. Create or update sale in Odoo
      3. Get artwork from artwork service
      4. Confirm sale in Odoo
      5. Persist order as CONFIRMED
```

#### **CompletedSaleUseCase**
Workflow: Find Completed Sales → Update Order Status → Send Notifications

```python
CompletedSaleUseCase.execute():
  for each order_service:
    for each completed_sale in sale_service:
      1. Load order from provider cache
      2. Update order status to COMPLETED
      3. Send delivery notification (EDIFACT)
```

#### **StockTransferUseCase**
Workflow: Read Stock Requests → Process Transfers → Reply to Provider

```python
StockTransferUseCase.execute():
  for each stock_service:
    for each stock_transfer:
      1. Read transfer request
      2. Process transfer (validate, update inventory)
      3. Reply to provider with status
```

## Setup and Installation

### Prerequisites

- **Python 3.12+** (check with `python --version`)
- **uv** package manager ([install from](https://docs.astral.sh/uv/))
- **sale.order required fields**: x_remote_delivery_instructions (char), x_remote_notified_completion (bool), x_remote_order_id (char), x_remote_order_provider (char)
- **sale.order sql update**: "update sale_order set x_remote_order_provider = 'HARMAN JBL' where x_remote_order_provider = 'Harman INSDES'"
- **res.partner required fields**: x_remote_order_id (char), x_remote_order_provider (char)
- **res.partner sql update**: "update res_partner set x_remote_order_provider = 'HARMAN JBL' where x_remote_order_provider = 'Harman INSDES'"

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd deonet-external-order
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Verify installation**
   ```bash
   uv run pytest tests/ -q
   # Should show: 894 passed in 0.85s
   ```

### Development Setup

For active development with type checking:

```bash
# Install dev dependencies
uv sync --group dev

# Run tests with coverage
uv run pytest tests/ --cov=src

# Run type checking (if using pyright/mypy)
uv run pyright src/
```

## Configuration

Configuration is centralized in `src/config.py` and loaded from environment variables.

### Configuration File: `config.py`

```python
@dataclass(frozen=True, slots=True)
class Config:
    # Directories
    work_dir: Path = Path.home() / "projects_data" / "external_order"
    templates_dir: Path                          # Auto-set to src/templates
    harman_input_dir: Path                       # Auto-set from work_dir
    harman_output_dir: Path
    digitals_dir: Path
    open_orders_dir: Path
    
    # Harman settings
    harman_administration_id: int = 2
    harman_customer_id: int = 5380
    harman_pricelist_id: int = 2
    harman_order_provider: str = "HARMAN JBL"
    harman_shipment_type: str = "harman%"
    harman_workdays_for_delivery: int = 2
    
    # Odoo settings
    odoo_base_url: str                           # from env ODOO_BASE_URL
    odoo_database: str                           # from env ODOO_DATABASE
    odoo_rpc_user_id: int                        # from env ODOO_RPC_USER_ID
    odoo_rpc_password: str                       # from env ODOO_RPC_PASSWORD
    
    # Spectrum settings
    spectrum_base_url: str                       # from env SPECTRUM_BASE_URL
    spectrum_api_key: str                        # from env SPECTRUM_API_KEY
```

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Working Directory (optional, defaults to ~/projects_data/external_order)
WORK_DIR=/path/to/work/directory

# SSL Verification (optional, defaults to true for production)
SSL_VERIFY=true

# Email/SMTP Settings (optional, for notifications and alerts)
SMTP_HOST=smtp-relay.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your_email@company.com
EMAIL_ALERT_TO=alert@company.com
EMAIL_STOCK_TO=stock@company.com

# Odoo ERP (required for sales operations)
ODOO_BASE_URL=https://odoo.company.com
ODOO_DATABASE=production_db
ODOO_RPC_USER_ID=2
ODOO_RPC_PASSWORD=your_odoo_token_here

# Spectrum Artwork Service (required for artwork retrieval)
SPECTRUM_BASE_URL=https://staging.spectrumcustomizer.com/
SPECTRUM_API_KEY=your_spectrum_token_here
```

**Environment Variable Reference:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORK_DIR` | No | `~/projects_data/external_order` | Base directory for working files, logs, and order tracking |
| `SSL_VERIFY` | No | `true` | Enable/disable SSL certificate verification for HTTPS requests |
| `SMTP_HOST` | No | `smtp-relay.gmail.com` | SMTP server host for email notifications |
| `SMTP_PORT` | No | `587` | SMTP server port (TLS) |
| `EMAIL_SENDER` | No | Empty | Sender email address for notifications |
| `EMAIL_ALERT_TO` | No | Empty | Comma-separated email addresses for alerts |
| `EMAIL_STOCK_TO` | No | Empty | Comma-separated email addresses for stock transfer notifications |
| `ODOO_BASE_URL` | Yes | Empty | Base URL for Odoo JSON-RPC API |
| `ODOO_DATABASE` | Yes | Empty | Odoo database/instance name |
| `ODOO_RPC_USER_ID` | Yes | `0` | Numeric user ID for Odoo JSON-RPC API authentication |
| `ODOO_RPC_PASSWORD` | Yes | Empty | Odoo user password for JSON-RPC API authentication |
| `SPECTRUM_BASE_URL` | Yes | Empty | Base URL for Spectrum artwork API |
| `SPECTRUM_API_KEY` | Yes | Empty | API key for Spectrum authentication |

### Using Configuration

```python
from src.config import get_config

# Get singleton config instance (cached)
config = get_config()

# Access settings
harman_input = config.harman_input_dir
odoo_url = config.odoo_base_url
```

## Domain Entities

### Order (Aggregate Root)

The `Order` class represents a single order from an external provider:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Order:
    administration_id: int           # Provider administration ID
    customer_id: int                 # Customer/distributor ID
    order_provider: str              # "Harman", "MyProvider", etc.
    pricelist_id: int
    remote_order_id: str             # ID in external system
    shipment_type: str               # Shipping method
    description: str                 # Order description/summary
    delivery_instructions: str = ""  # Optional delivery instructions
    status: OrderStatus              # NEW, CREATED, ARTWORK, CONFIRMED, COMPLETED
    ship_to: ShipTo                  # Shipping address
    line_items: list[LineItem]       # Order lines with products
    
    # Read-only fields
    id: UUID                         # Local unique ID
    sale_id: int                     # Odoo sale ID (once created)
    created_at: datetime
    ship_at: date
```

**OrderStatus enum:**
```
NEW → CREATED → ARTWORK → CONFIRMED → COMPLETED → SHIPPED
                                            ↓
                                         FAILED
```

### ShipTo (Value Object)

Represents a shipping address:

```python
@dataclass(frozen=True, slots=True)
class ShipTo:
    remote_customer_id: str          # ID in external system
    company_name: str
    contact_name: str                # Validated: title case
    email: str                       # Validated: contains @ and .
    phone: str                       # Validated: basic format
    street1: str
    street2: str = ""
    city: str
    state_code: str = ""
    postal_code: str
    country_code: str                # Validated: 2-letter ISO code
```

### LineItem (Value Object)

```python
@dataclass(frozen=True, slots=True)
class LineItem:
    line_number: int
    product_code: str
    quantity: int                    # Positive integer
    unit_price: float
    total_price: float = 0.0
```

### Artwork (Value Object)

```python
@dataclass(frozen=True, slots=True)
class Artwork:
    product_code: str
    material: str                    # "CLEAR", "STANDARD", etc.
    file_path: Path
    created_at: datetime = field(default_factory=lambda: datetime.now())
```

### Validators

Every domain object is validated on creation. Validators are in `src/domain/validators.py`:

```python
validate_email(value, field_name)              # Checks @ and .
validate_phone(value, field_name)              # Basic format validation
validate_country_code(value, field_name)       # 2-letter ISO code
validate_positive_int(value, field_name)       # > 0
validate_non_negative_int(value, field_name)   # >= 0
validate_non_empty_string_uppercase(value)     # Converts and validates
```

## Adding New Services

### 1. Adding a New Order Provider

**Goal:** Add support for a new order provider (e.g., "MyProvider").

#### Step 1: Implement IOrderService Interface

Create `src/services/myprovider_order_service.py`:

```python
from src.interfaces import IOrderService, IErrorQueue, IRegistry, IArtworkService
from src.domain import Order, OrderStatus

@dataclass(frozen=True, slots=True, kw_only=True)
class MyProviderOrderService:
    """Order service for MyProvider."""
    
    # Add any required configuration or clients
    api_url: str
    api_key: str
    input_dir: Path
    
    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Create from global config."""
        return cls(
            api_url=config.myprovider_api_url,  # Add to config
            api_key=config.myprovider_api_key,
            input_dir=config.open_orders_dir,
        )
    
    # IOrderReader
    def read_orders(self) -> Generator[Order, None, None]:
        """Read orders from MyProvider API."""
        response = httpx.get(f"{self.api_url}/orders", headers={
            "Authorization": f"Bearer {self.api_key}"
        })
        for raw_order in response.json()["orders"]:
            yield self._parse_order(raw_order)
    
    def _parse_order(self, raw_order: dict) -> Order:
        """Convert raw API order to Order domain object."""
        return Order(
            administration_id=raw_order["admin_id"],
            customer_id=raw_order["customer_id"],
            order_provider="MyProvider",
            pricelist_id=raw_order.get("pricelist_id", 1),
            remote_order_id=raw_order["order_id"],
            shipment_type=raw_order.get("shipment_type", "standard"),
            description=raw_order.get("description", f"MyProvider Order {raw_order['order_id']}"),
            delivery_instructions=raw_order.get("delivery_instructions", ""),
            ship_to=ShipTo(
                remote_customer_id=raw_order["ship_to"]["customer_id"],
                company_name=raw_order["ship_to"]["company"],
                contact_name=raw_order["ship_to"]["contact"],
                email=raw_order["ship_to"]["email"],
                phone=raw_order["ship_to"]["phone"],
                street1=raw_order["ship_to"]["street"],
                city=raw_order["ship_to"]["city"],
                postal_code=raw_order["ship_to"]["zip"],
                country_code=raw_order["ship_to"]["country"],
            ),
            line_items=[
                LineItem(
                    line_number=line["line_no"],
                    product_code=line["sku"],
                    quantity=line["qty"],
                    unit_price=line["price"],
                )
                for line in raw_order["lines"]
            ],
        )
    
    # IOrderStore
    def persist_order(self, order: Order, status: OrderStatus) -> None:
        """Save order status to MyProvider (or local cache)."""
        # Example: POST to MyProvider API
        # Or: Save to local JSON file
        order_file = self.input_dir / f"{order.remote_order_id}.json"
        order_file.write_text(json.dumps({
            "remote_order_id": order.remote_order_id,
            "status": status.value,
            "sale_id": order.sale_id,
        }))
    
    def load_order(self, remote_order_id: str) -> Order | None:
        """Load saved order from cache."""
        order_file = self.input_dir / f"{remote_order_id}.json"
        if not order_file.exists():
            return None
        # Reconstruct Order from cached data
        # (Implementation depends on what you cached)
    
    # IOrderNotifier
    def notify_completed_sale(self, order: Order) -> None:
        """Notify MyProvider that sale is completed."""
        # Send EDIFACT notification or API call
        # Example:
        #   httpx.post(f"{self.api_url}/orders/{order.remote_order_id}/notify",
        #              json={"status": "completed", "sale_id": order.sale_id})
    
    # IArtworkServiceProvider
    def get_artwork_service(
        self, order: Order, artwork_services: IRegistry[IArtworkService]
    ) -> IArtworkService | None:
        """Select artwork service based on order."""
        # Logic to pick which artwork service to use
        # For MyProvider orders, use Spectrum
        return artwork_services.get("Spectrum")
```

#### Step 2: Register in main.py

```python
# src/main.py
from src.services.myprovider_order_service import MyProviderOrderService

def main() -> None:
    config = get_config()
    order_services = Registry[IOrderService]()
    
    # Register existing providers
    order_services.register("Harman", HarmanOrderService.from_config(config))
    
    # Register new provider
    order_services.register("MyProvider", MyProviderOrderService.from_config(config))
    
    # Rest of main() uses order_services.items() - works for all providers!
```

#### Step 3: Add Configuration

```python
# src/config.py - add to Config class
@dataclass(frozen=True, slots=True)
class Config:
    # ... existing config ...
    
    # MyProvider settings
    myprovider_api_url: str = os.getenv("MYPROVIDER_API_URL", "")
    myprovider_api_key: str = os.getenv("MYPROVIDER_API_KEY", "")
```

```bash
# .env
MYPROVIDER_API_URL=https://api.myprovider.com
MYPROVIDER_API_KEY=your_api_key
```

### 2. Adding a New Artwork Service

**Goal:** Add a new artwork provider (e.g., "LocalFilesystem").

Create `src/services/local_filesystem_artwork_service.py`:

```python
from src.interfaces import IArtworkService
from src.domain import Order

@dataclass(frozen=True, slots=True, kw_only=True)
class LocalFilesystemArtworkService:
    """Get artwork from local filesystem."""
    
    artwork_dir: Path
    
    def get_artwork(self, order: Order) -> list[Path]:
        """Fetch artwork files from local filesystem."""
        artwork_files = []
        for line_item in order.line_items:
            product_dir = self.artwork_dir / line_item.product_code
            if product_dir.exists():
                artwork_files.extend(product_dir.glob("*.pdf"))
        return artwork_files
```

Register in `main.py`:

```python
artwork_services.register("LocalFS", LocalFilesystemArtworkService(
    artwork_dir=config.digitals_dir
))
```

### 3. Adding a New Stock Service

**Goal:** Add a new stock/inventory provider.

Create `src/services/myprovider_stock_service.py`:

```python
from src.interfaces import IStockService, IErrorQueue

@dataclass(frozen=True, slots=True, kw_only=True)
class MyProviderStockService:
    """Handle stock transfers with MyProvider."""
    
    api_url: str
    api_key: str
    
    def read_stock_transfers(self) -> Generator[dict, None, None]:
        """Read pending stock transfer requests."""
        response = httpx.get(f"{self.api_url}/stock_transfers",
                           headers={"Authorization": f"Bearer {self.api_key}"})
        for transfer in response.json()["transfers"]:
            yield transfer
    
    def reply_stock_transfer(self, transfer_data: dict[str, Any]) -> None:
        """Confirm stock transfer completion."""
        httpx.post(f"{self.api_url}/stock_transfers/{transfer_data['id']}/confirm",
                  json={"status": "completed"})
```

Register in `main.py`:

```python
stock_services.register("MyProvider", MyProviderStockService.from_config(config))
```

## Testing

### Test Coverage

Current coverage: **894 tests passing** with comprehensive test suites

- **Unit tests** (893+) - Individual component testing with mocks
- **Integration tests** (27+) - Cross-module testing with pytest-httpx
- **Documentation** - All modules have comprehensive docstrings

Run tests:

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/domain/test_order.py -v

# Run specific test class
uv run pytest tests/unit/services/test_odoo_sale_service.py::TestOdooSaleService -v
```

### Writing Tests for New Services

Example: Testing `MyProviderOrderService`

```python
# tests/unit/services/test_myprovider_order_service.py
import pytest
from unittest.mock import Mock
import httpx
from pytest_httpx import HTTPXMock

from src.services.myprovider_order_service import MyProviderOrderService

class TestMyProviderOrderService:
    
    @pytest.fixture
    def service(self):
        return MyProviderOrderService(
            api_url="https://api.test.com",
            api_key="test_key",
            input_dir=Path("/tmp"),
        )
    
    def test_read_orders_success(self, service, httpx_mock: HTTPXMock):
        """Test reading orders from API."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.test.com/orders",
            json={
                "orders": [
                    {
                        "order_id": "ORD001",
                        "admin_id": 1,
                        "customer_id": 100,
                        # ... more fields
                    }
                ]
            }
        )
        
        orders = list(service.read_orders())
        
        assert len(orders) == 1
        assert orders[0].remote_order_id == "ORD001"
```

## Error Handling

### Error Store Pattern

Instead of exceptions propagating up the stack and stopping execution, they're collected centrally in ErrorStore:

```python
# In main.py
error_store = ErrorStore()

# Execute each use case, collecting errors
for _, use_case in use_cases.items():
    try:
        use_case.execute()
    except Exception as exc:
        error_store.add(exc)
        logger.error(f"Error executing use case: {exc!s}")

# At the end, check if errors occurred and send alert email
if error_store.has_errors():
    emailer = EmailSender(...)
    emailer.send(
        subject="Deonet External Order - Errors during execution",
        body_params=error_store.get_render_email_data(),
    )
```

This ensures that:
- One failing service doesn't stop other services from executing
- All errors are collected and reported together
- The IT team receives an email alert with complete error details
- Execution continues even if individual orders fail

### Custom Error Types

```python
# src/app/errors.py

class SaleError(Exception):
    """Error during sale creation/processing."""
    def __init__(self, message: str, order_id: str):
        self.order_id = order_id
        super().__init__(message)

class NotifyError(Exception):
    """Error during order notification."""
    def __init__(self, message: str, order_id: str):
        self.order_id = order_id
        super().__init__(message)

class ArtworkError(Exception):
    """Error during artwork retrieval."""
    pass
```

Throw errors for critical failures:

```python
# In order service
if not order_data:
    raise NotifyError("No valid order data found", order_id=order.remote_order_id)
```

## Development Workflow

### Code Style & Conventions

- **Type hints** are required on all functions and classes
- **Comprehensive docstrings** required:
  - Module docstrings: Concise one/two-line purpose description
  - Class docstrings: Clear purpose with Attributes section for dataclasses
  - Method/function docstrings: Args, Returns, Raises sections for complex methods, one-liners for simple ones
  - All core modules standardized with consistent style (see spectrum_artwork_service.py as reference)
  - Action-oriented language preferred ("Retrieve", "Parse", "Create", "Validate")
- **Frozen dataclasses** used for immutable domain objects with validation in `__post_init__()`
- **Protocols** instead of abstract base classes for interfaces (contract-based design)
- **Single responsibility** - each class has one reason to change
- **Error handling**: Exceptions collected in ErrorStore, not propagated (fail-safe pattern)

### Project Structure Decisions

1. **`src/` directory structure mirrors DDD layers:**
   - Domain → no external dependencies
   - Services → external integrations
   - App → orchestration/coordination
   - Interfaces → contracts

2. **Services are stateless:**
   - No internal state mutation
   - Accept parameters, return results
   - Thread-safe by default

3. **Validation at the boundary:**
   - Domain objects validate on creation
   - Services validate inputs before processing
   - Use case layer catches and logs exceptions

### Adding a New Module

If you need to add a new cross-cutting concern (e.g., logging, caching):

```python
# src/utils/cache.py (new utility module)
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_expensive_operation(key: str) -> Result:
    """Cache results of expensive operation."""
    pass

# Then import and use in services
from src.utils.cache import cached_expensive_operation
```

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-service

# Make changes, test, commit
uv run pytest tests/ -v  # Verify all 894 tests pass
git add .
git commit -m "Add new artwork service"

# Push and create PR
git push origin feature/new-service

# Before merging:
# 1. Verify all tests pass with: uv run pytest -q (expect ~894 tests, 94% coverage)
# 2. Ensure new code has type hints and comprehensive docstrings
# 3. Check that error handling collects to ErrorStore singleton (not print/raise)
```

## Dependencies

### Production Dependencies

| Package         | Purpose                                          |
| --------------- | ------------------------------------------------ |
| `requests`      | HTTP client for API calls with timeout support   |
| `jinja2`        | Template engine for EDIFACT rendering            |
| `pydifact`      | EDIFACT EDI message parsing/generation           |
| `python-dotenv` | Environment variable loading from `.env` files   |
| `redmail`       | SMTP email client for error alerts and notifications |
| `xmltodict`     | XML to dictionary conversion (Harman stock API)  |

### Development Dependencies

| Package        | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `pytest`       | Test runner & assertion framework (894 tests)       |
| `pytest-cov`   | Code coverage measurement (94% coverage)             |
| `pytest-mock`  | Mocking and patching utilities                       |
| `types-requests` | Type hints for requests library                    |

### Why These Choices

**Production Packages:**
- **requests** - Widely used HTTP client with clear API, excellent error handling, robust connection management
- **Jinja2** - Industry standard for templating, excellent EDIFACT format support, powerful expression language
- **pydifact** - Purpose-built EDIFACT parser vs rolling our own, handles D96A/D99A EDI standards correctly
- **python-dotenv** - Simple, convention-based config management, works well with 12-factor app principles
- **redmail** - High-level SMTP wrapper that simplifies email sending with template support
- **xmltodict** - Lightweight XML-to-dict conversion for Harman stock API responses

**Development Packages:**
- **pytest** - Superior fixture system, better assertions, excellent plugin ecosystem (pytest-mock, pytest-cov)
- **pytest-cov** - Integrated coverage reporting with HTML output via `--cov-report=html`
- **pytest-mock** - Cleaner mocking API than unittest.mock, better pytest integration
- **types-requests** - Type hints for requests library, enables better IDE support and type checking

## Project Status

### Latest Release Highlights

✅ **All 894 Tests Passing with 94% Coverage**
- 856+ unit tests for isolated component testing
- 38 integration tests for cross-module workflows
- Full coverage: 1054 statements, 59 lines missing (mostly edge cases and defensive checks)
- Run with: `uv run pytest -q` or `uv run pytest --cov=src` for coverage report

✅ **Standardized Docstrings with Args/Returns/Raises Sections**
- **All core modules** - Comprehensive docstrings following spectrum_artwork_service.py style
- **Service methods** - Args, Returns, Raises sections for complex operations
- **Domain models** - Clear purpose with Attributes documentation
- **Interfaces** - 13+ Protocol definitions with method contracts
- **Complete implementation** - 5 service implementations with full test coverage:
  - HarmanOrderService - EDIFACT order EDI processing (52 tests, 83% coverage)
  - HarmanStockService - Stock transfer handling (23 tests, 100% coverage)
  - OdooSaleService - JSON-RPC CRM integration (59 tests, 99% coverage)
  - RenderService - Jinja2 template rendering (33 tests, 100% coverage)
  - SpectrumArtworkService - Artwork retrieval and management (35 tests, 100% coverage)

✅ **Simplified Error Handling**
- Centralized ErrorStore pattern for collecting exceptions
- Email alerts sent to IT team with complete error details
- Fail-safe design ensures partial failures don't block other services
- All use cases continue executing even if individual orders fail

### Architecture Quality

- **Clean Architecture** - Strict separation of concerns (Domain, App, Services, Interfaces)
- **Plugin Architecture** - Service registries allow runtime registration of new providers
- **Protocol-Based Interfaces** - Contract-driven design using Python Protocols
- **Immutable Domain Objects** - Frozen dataclasses with validation in `__post_init__()`
- **Type-Safe** - Full type hints on all functions and classes
- **Well-Tested** - 894 tests with 94% coverage providing strong regression protection

### Ready for Production

This codebase is production-ready with:
- Complete test coverage of core workflows
- Comprehensive documentation for all modules and classes
- Robust error handling and alerting
- Clean, maintainable architecture supporting extension and modification

### Adding New Dependencies

```bash
# Add production dependency
uv add new-package

# Add dev-only dependency
uv add --group dev new-dev-package

# Update lock file
uv sync
```

---

## Quick Reference

### Common Commands

```bash
# Setup
uv sync                                    # Install all dependencies

# Development
uv run pytest tests/ -v                    # Run all 894 tests
uv run pytest tests/ --cov=src             # With coverage report
uv run pytest tests/ --cov-report=html     # HTML coverage report
uv run python -m src.main                  # Run application

# Configuration
export ODOO_BASE_URL="https://..."
export SPECTRUM_API_KEY="..."
uv run python -m src.main

# Code quality
uv run pytest tests/ -q                    # Quiet output (expect 894 passed)
uv run pytest tests/ --lf                  # Last failed tests only
uv run pytest tests/ -k test_name          # Run specific test
```

### Key Files to Understand

1. **`src/main.py`** - Start here to understand the overall flow
2. **`src/interfaces/base.py`** - Understand the service contracts
3. **`src/app/new_sale_use_case.py`** - See how use cases orchestrate services
4. **`src/services/harman_order_service.py`** - Example of a complete service implementation
5. **`src/config.py`** - Configuration management

---

**Questions? Issues? Submit them to the project's issue tracker.**
