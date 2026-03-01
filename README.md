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
│   │   ├── error_handler.py                # Centralized error handling
│   │   └── errors.py                       # Custom exception types
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
    for order in order_service.read_orders(error_queue):
        # Process order
```

#### 2. **Protocol-Based Interfaces**

Services implement Python Protocol interfaces (like TypeScript interfaces). Each protocol defines a specific capability:

- `IOrderReader` - Read orders from a provider
- `IOrderStore` - Persist order state
- `IOrderNotifier` - Send notifications
- `IArtworkServiceProvider` - Select artwork service for order
- `IOrderService` - Full-featured order provider (combines all above)

#### 3. **Separation of Concerns**

- **App Layer** - Orchestration & workflow (use cases)
- **Domain Layer** - Business rules & validation (order, line items, etc.)
- **Service Layer** - External system integration (Odoo, Harman, Spectrum)
- **Interface Layer** - Contracts between layers (protocols)

#### 4. **Error Queue Pattern**

Instead of throwing exceptions up the call stack, errors are collected in a queue for centralized handling:

```python
error_queue: IErrorQueue = ErrorQueue()
for order in order_service.read_orders(error_queue):
    try:
        # Process order
    except Exception as exc:
        error_handler.handle_order_error(exc, order_id, service_name, context)

# Summarize all errors at the end
logger.error(error_queue.summarize())
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
   # Should show: 858 passed in 1.34s
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
    harman_order_provider: str = "Harman INSDES"
    harman_shipment_type: str = "harman%"
    harman_workdays_for_delivery: int = 2
    
    # Odoo settings
    odoo_base_url: str                           # from env ODOO_BASE_URL
    odoo_database: str                           # from env ODOO_DATABASE
    odoo_rpc_user_id: int                        # from env ODOO_USER_ID
    odoo_rpc_password: str                       # from env ODOO_PASSWORD
    
    # Spectrum settings
    spectrum_base_url: str                       # from env SPECTRUM_BASE_URL
    spectrum_api_key: str                        # from env SPECTRUM_API_KEY
```

### Environment Variables

Create a `.env` file:

```bash
# Directories (optional, defaults shown above)
WORK_DIR=/path/to/work/directory

# Harman settings (optional, defaults shown above)
HARMAN_ADMINISTRATION_ID=2
HARMAN_CUSTOMER_ID=5380
HARMAN_PRICELIST_ID=2
HARMAN_ORDER_PROVIDER="Harman INSDES"
HARMAN_SHIPMENT_TYPE="harman%"
HARMAN_WORKDAYS_FOR_DELIVERY=2

# Odoo ERP (required)
ODOO_BASE_URL=https://odoo.company.com
ODOO_DATABASE=production_db
ODOO_USER_ID=2
ODOO_PASSWORD=your_password_here

# Spectrum Artwork Service (required)
SPECTRUM_BASE_URL=https://spectrum-api.company.com
SPECTRUM_API_KEY=your_api_key_here
```

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
    def read_orders(self, error_queue: IErrorQueue) -> Generator[Order, None, None]:
        """Read orders from MyProvider API."""
        try:
            response = httpx.get(f"{self.api_url}/orders", headers={
                "Authorization": f"Bearer {self.api_key}"
            })
            for raw_order in response.json()["orders"]:
                yield self._parse_order(raw_order)
        except Exception as e:
            error_queue.put(e)
    
    def _parse_order(self, raw_order: dict) -> Order:
        """Convert raw API order to Order domain object."""
        return Order(
            administration_id=raw_order["admin_id"],
            customer_id=raw_order["customer_id"],
            order_provider="MyProvider",
            pricelist_id=raw_order.get("pricelist_id", 1),
            remote_order_id=raw_order["order_id"],
            shipment_type=raw_order.get("shipment_type", "standard"),
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
    
    def read_stock_transfers(self, error_queue: IErrorQueue) -> Generator[dict, None, None]:
        """Read pending stock transfer requests."""
        try:
            response = httpx.get(f"{self.api_url}/stock_transfers",
                               headers={"Authorization": f"Bearer {self.api_key}"})
            for transfer in response.json()["transfers"]:
                yield transfer
        except Exception as e:
            error_queue.put(e)
    
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

Current coverage: **96%** across 858 tests

- **Unit tests** (790+) - Individual component testing with mocks
- **Integration tests** (26+) - Cross-module testing with pytest-httpx

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
from src.app.errors import ErrorQueue

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
        
        error_queue = ErrorQueue()
        orders = list(service.read_orders(error_queue))
        
        assert len(orders) == 1
        assert orders[0].remote_order_id == "ORD001"
```

## Error Handling

### Error Queue Pattern

Instead of exceptions propagating up the stack, they're collected centrally:

```python
# In use cases
error_queue: IErrorQueue = ErrorQueue()

for order_service_name, order_service in order_services.items():
    for order in order_service.read_orders(error_queue):
        try:
            # Process order
        except Exception as exc:
            # Don't crash - collect the error
            error_handler.handle_order_error(exc, order_id, service_name, "context")

# At the end, summarize all errors
print(error_queue.summarize())
```

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
- **Docstrings** required for modules, classes, and public methods
- **Frozen dataclasses** used for immutable domain objects
- **Protocols** instead of abstract base classes for interfaces
- **Single responsibility** - each class has one reason to change

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
uv run pytest tests/ -v  # Verify all tests pass
git add .
git commit -m "Add new artwork service"

# Push and create PR
git push origin feature/new-service
```

## Dependencies

### Production Dependencies

| Package         | Purpose                                          |
| --------------- | ------------------------------------------------ |
| `httpx`         | Modern HTTP client with async support            |
| `jinja2`        | Template engine for EDIFACT rendering            |
| `pydifact`      | EDIFACT EDI message parsing/generation           |
| `python-dotenv` | Environment variable loading from `.env` files   |
| `xmltodict`     | XML to dictionary conversion (future: if needed) |

### Development Dependencies

| Package        | Purpose                           |
| -------------- | --------------------------------- |
| `pytest`       | Test runner & assertion framework |
| `pytest-cov`   | Code coverage measurement         |
| `pytest-mock`  | Mocking and patching utilities    |
| `pytest-httpx` | Mock HTTP responses for testing   |

### Why These Choices

- **httpx** over `requests` - Better async support, modern API
- **Jinja2** - Industry standard for templating, plays well with EDIFACT
- **pydifact** - Specialized EDIFACT parsing vs rolling our own
- **python-dotenv** - Simple, convention-based config management
- **pytest** - Superior fixture system, better output, active community

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
uv sync                          # Install all dependencies

# Development
uv run pytest tests/ -v          # Run all tests
uv run pytest tests/ --cov=src   # With coverage
uv run python -m src.main        # Run application

# Configuration
export ODOO_BASE_URL="https://..."
export SPECTRUM_API_KEY="..."
uv run python -m src.main

# Code quality
uv run pytest tests/ -q          # Quiet output
uv run pytest tests/ --lf        # Last failed tests only
```

### Key Files to Understand

1. **`src/main.py`** - Start here to understand the overall flow
2. **`src/interfaces/base.py`** - Understand the service contracts
3. **`src/app/new_sale_use_case.py`** - See how use cases orchestrate services
4. **`src/services/harman_order_service.py`** - Example of a complete service implementation
5. **`src/config.py`** - Configuration management

---

**Questions? Issues? Submit them to the project's issue tracker.**
