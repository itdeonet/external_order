# Architecture Diagram - Deonet External Order Processing

## Component Architecture

```mermaid
graph TD
    Main["MAIN<br/>(Entry Point)<br/>- Initialize Config<br/>- Create Registries<br/>- Orchestrate Use Cases"]
    
    UC["USE CASES<br/>(App Layer)<br/>- NewSaleUseCase<br/>- CompletedSaleUseCase<br/>- StockTransferUseCase"]
    
    Reg["REGISTRIES<br/>(Service Discovery)<br/>- IRegistry[T]<br/>- Thread-safe"]
    
    OrderSvc["HarmanOrderService<br/>- read_orders()<br/>- persist_order()<br/>- load_order()<br/>- notify_completed_sale()"]
    
    SaleSvc["OdooSaleService<br/>- create_sale()<br/>- update_contact()<br/>- confirm_sale()<br/>- mark_sale_notified()"]
    
    ArtSvc["SpectrumArtworkService<br/>- get_artwork()<br/>- _load_order_data()<br/>- _download_designs()"]
    
    StockSvc["HarmanStockService<br/>- read_stock_transfers()<br/>- create_stock_transfer_reply()<br/>- email_stock_transfer_reply()<br/>- mark_transfer_as_processed()"]
    
    Odoo["ODOO SYSTEM<br/>(JSON-RPC 2.0)<br/>- sale.order<br/>- res.partner<br/>- product.product<br/>- delivery.carrier"]
    
    Harman["HARMAN<br/>File System<br/>- harman/in<br/>- harman/out<br/>- *.edifact, *.xml"]
    
    Spectrum["SPECTRUM API<br/>REST Endpoints<br/>- /api/order/<br/>- /api/webtoprint/<br/>- /spec.../pdf"]
    
    Main --> UC
    Main --> Reg
    UC --> OrderSvc
    UC --> SaleSvc
    UC --> ArtSvc
    UC --> StockSvc
    Reg -.->|orders, artwork,<br/>sale services| UC
    OrderSvc --> Odoo
    OrderSvc --> Harman
    SaleSvc --> Odoo
    ArtSvc --> Spectrum
    StockSvc --> Harman
```

## Data Flow Diagram

### New Sale Workflow
```mermaid
graph TD
    Start["Harman EDIFACT File"]
    Read["HarmanOrderService.read_orders()"]
    Parse["Parser.parse()"]
    Order["Order<br/>(domain model)"]
    
    NewSale["NewSaleUseCase.execute()"]
    Persist1["persist_order(NEW)"]
    Search["OdooSaleService.search_sale()"]
    
    Create["create_sale()"]
    Contact["search/create contact"]
    Convert["convert order lines"]
    RPC1["RPC: sale.order.create()"]
    
    Persist2["persist_order(CREATED)"]
    GetArt["HarmanOrderService.get_artwork_service()"]
    RetArt["Return SpectrumArtworkService<br/>if matches"]
    
    GetArtwork["SpectrumArtworkService.get_artwork()"]
    API1["API: GET /api/order/"]
    API2["API: GET /api/webtoprint/"]
    Extract["Extract ZIP to digitals_dir"]
    API3["API: GET /spec.../pdf/"]
    SavePDF["Save PDF to digitals_dir"]
    SetArt["LineItem.set_artwork(Artwork)"]
    
    Org["organize_placement_files()"]
    Copy["Copy to open_orders_dir/{sale_id}/"]
    
    Persist3["persist_order(ARTWORK)"]
    Confirm["OdooSaleService.confirm_sale()"]
    RPC2["RPC: sale.order.action_confirm()"]
    Persist4["persist_order(CONFIRMED)"]
    
    Output["✓ Sale created in Odoo<br/>with artwork"]
    
    Start --> Read
    Read --> Parse
    Parse --> Order
    Order --> NewSale
    NewSale --> Persist1
    Persist1 --> Search
    Search -->|Yes: check update| Persist2
    Search -->|No: create| Create
    Create --> Contact
    Contact --> Convert
    Convert --> RPC1
    RPC1 --> Persist2
    Persist2 --> GetArt
    GetArt --> RetArt
    RetArt --> GetArtwork
    GetArtwork --> API1
    API1 --> API2
    API2 --> Extract
    API2 --> API3
    API3 --> SavePDF
    GetArtwork --> SetArt
    SetArt --> Org
    Org --> Copy
    Copy --> Persist3
    Persist3 --> Confirm
    Confirm --> RPC2
    RPC2 --> Persist4
    Persist4 --> Output
```

### Completed Sale Workflow
```mermaid
graph TD
    Search["OdooSaleService.search_completed_sales()"]
    RPC0["RPC: sale.order.search_read()"]
    Filter["Filter: state=done, not notified"]
    
    Execute["CompletedSaleUseCase.execute()"]
    Loop["For each sale_id, remote_order_id"]
    
    Load["HarmanOrderService.load_order()"]
    LoadFile["Load from work_dir/{remote_id}.json"]
    
    GetNotify["HarmanOrderService.get_notify_data()"]
    SearchShip["search_shipping_info()"]
    SearchSerial["search_serials_by_line_item()"]
    PrepNotify["Prepare notification dict"]
    
    Notify["HarmanOrderService.notify_completed_sale()"]
    Render1["RenderService.render()"]
    Template1["desadvd96a.j2<br/>(Jinja2)"]
    Render2["RenderService.render()"]
    Template2["desadvd99a.j2<br/>(Jinja2)"]
    Serial["Serializer.serialize()"]
    EDIFACT["EDIFACT text"]
    WriteFile["Write to harman/out/"]
    
    Mark["OdooSaleService.mark_sale_notified()"]
    RPC1["RPC: sale.order.write()<br/>x_sale_notified=True"]
    
    Persist["persist_order(COMPLETED)"]
    
    Output["✓ DESADV files +<br/>Odoo updated"]
    
    Search --> RPC0
    RPC0 --> Filter
    Filter --> Execute
    Execute --> Loop
    Loop --> Load
    Load --> LoadFile
    LoadFile --> GetNotify
    GetNotify --> SearchShip
    GetNotify --> SearchSerial
    SearchShip --> PrepNotify
    SearchSerial --> PrepNotify
    PrepNotify --> Notify
    Notify --> Render1
    Render1 --> Template1
    Notify --> Render2
    Render2 --> Template2
    Notify --> Serial
    Serial --> EDIFACT
    EDIFACT --> WriteFile
    WriteFile --> Mark
    Mark --> RPC1
    RPC1 --> Persist
    Persist --> Output
```

### Stock Transfer Workflow
```mermaid
graph TD
    XML["Harman XML File<br/>(DELVRY03 IDOC)"]
    Read["HarmanStockService.read_stock_transfers()"]
    Parse["xmltodict.parse()"]
    Extract["Extract delivery info,<br/>idoc_number, items"]
    
    Execute["StockTransferUseCase.execute()"]
    
    CreateReply["HarmanStockService.create_stock_transfer_reply()"]
    Build["Build IN05 IDOC dict<br/>from transfer_data"]
    Unparse["xmltodict.unparse()"]
    WriteXML["Write harman/out/<br/>HARMAN_IN05_{delivery_id}.XML"]
    ReturnPath["Return Path to reply file"]
    
    EmailReply["HarmanStockService.email_stock_transfer_reply()"]
    Template["Template: stock_email.html"]
    Attach["Attach: IN05 reply file"]
    Send["EmailSender.send()<br/>to configured recipients"]
    
    MarkProcessed["HarmanStockService.mark_transfer_as_processed()"]
    Rename["Rename input file<br/>to .PROCESSED"]
    
    Output["✓ IN05 reply created +<br/>Confirmation email sent +<br/>Input file marked processed"]
    
    XML --> Read
    Read --> Parse
    Parse --> Extract
    Extract --> Execute
    Execute --> CreateReply
    CreateReply --> Build
    Build --> Unparse
    Unparse --> WriteXML
    WriteXML --> ReturnPath
    ReturnPath --> EmailReply
    EmailReply --> Template
    EmailReply --> Attach
    Attach --> Send
    Send --> MarkProcessed
    MarkProcessed --> Rename
    Rename --> Output
```

## Service Registry Pattern

```mermaid
graph TD
    Protocol["IRegistry[T]<br/>register()<br/>get()<br/>unregister()<br/>clear()<br/>items()"]
    
    Impl["Registry[T]<br/>_registry: dict<br/>_lock: Lock<br/>Thread-safe methods"]
    
    OrderSvcs["Order Services<br/>HarmanOrderService"]
    ArtSvcs["Artwork Services<br/>SpectrumArtworkService"]
    StockSvcs["Stock Services<br/>HarmanStockService"]
    UseCases["Use Cases<br/>NewSaleUseCase<br/>CompletedSaleUseCase<br/>StockTransferUseCase"]
    
    Protocol --> Impl
    Impl --> OrderSvcs
    Impl --> ArtSvcs
    Impl --> StockSvcs
    Impl --> UseCases
```

## Domain Model Hierarchy

```mermaid
classDiagram
    class Order {
        administration_id: str
        customer_id: str
        order_provider: str
        pricelist_id: str
        remote_order_id: str
        shipment_type: str
        description: str
        delivery_instructions: str
        sale_id: str
        status: OrderStatus
        created_at: datetime
        ship_at: datetime
        ship_to: ShipTo
        line_items: List[LineItem]
        
        set_sale_id()
        set_status()
        set_created_at()
        set_ship_at()
        calculate_delivery_date()
    }
    
    class ShipTo {
        remote_customer_id: str
        company_name: str
        contact_name: str
        email: str
        phone: str
        street1: str
        street2: str
        city: str
        state_code: str
        postal_code: str
        country_code: str
    }
    
    class LineItem {
        line_id: str
        product_code: str
        quantity: int
        artwork: Artwork
        
        set_artwork()
    }
    
    class Artwork {
        artwork_id: str
        artwork_line_id: str
        design_paths: List[Path]
        created_at: datetime
    }
    
    class OrderStatus {
        <<enumeration>>
        NEW
        CREATED
        ARTWORK
        CONFIRMED
        COMPLETED
        SHIPPED
        FAILED
    }
    
    Order "1" --> "1" ShipTo : has
    Order "1" --> "*" LineItem : contains
    LineItem "0..1" --> "1" Artwork : has
    Order "*" --> "1" OrderStatus : has
```

## Error Handling Flow

```mermaid
graph TD
    Start["Use Case Execution"]
    Try["Try execute()"]
    
    NewSale["NewSaleUseCase"]
    Completed["CompletedSaleUseCase"]
    Stock["StockTransferUseCase"]
    
    TryCatch["Per-order Try/Catch"]
    OrderErr["Order-level errors<br/>Add to ErrorStore"]
    Continue["Continue next order"]
    
    Check{"ErrorStore.has_errors()?"}
    
    Yes["Yes"]
    CreateEmail["Create error email"]
    ErrorCount["- error_count<br/>- formatted issues<br/>- timestamp<br/>- company_name"]
    Send["EmailSender.send()<br/>template: error_alert.html"]
    
    No["No"]
    CleanExit["Clean exit"]
    
    Start --> Try
    Try --> NewSale
    Try --> Completed
    Try --> Stock
    NewSale --> TryCatch
    Completed --> TryCatch
    Stock --> TryCatch
    TryCatch --> OrderErr
    OrderErr --> Continue
    Continue --> Check
    Check --> Yes
    Yes --> CreateEmail
    CreateEmail --> ErrorCount
    ErrorCount --> Send
    Check --> No
    No --> CleanExit
```
