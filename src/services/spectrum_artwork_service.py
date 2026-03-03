"""Spectrum artwork service for retrieving digital assets from Spectrum API.

This module provides integration with the Spectrum web-to-print system for downloading
digital artwork assets (design files and specification PDFs) associated with order line items.
It manages the complete workflow of querying the Spectrum API for artwork metadata, matching
artwork to order line items, and downloading/extracting ZIP-archived design files and placement
PDFs to the local digitals directory.

Key Responsibilities:
- Query Spectrum API to retrieve order and line item artwork metadata
- Match Spectrum recipe set IDs with order line items by product code and quantity
- Download and extract ZIP-archived design files from Spectrum
- Download placement specification PDFs
- Organize files with sale ID prefixes for traceability

Typical Workflow:
1. get_artwork() receives an Order with populated line items
2. Queries /api/order/order-number/{remote_order_id}/ to get artwork metadata
3. Iterates through line items, matching them to Spectrum SKU/quantity combinations
4. For each matched line item, downloads designs (_get_designs) and placement (_get_placement)
5. Sets the Artwork object on the line item with URLs and local file paths
6. Returns list of all downloaded/extracted file paths

Error Handling:
Raises ArtworkError if any line item has no matching artwork in Spectrum, preventing
incomplete orders from proceeding to fulfillment.
"""

import io
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from zipfile import ZipFile

import httpx

from src.app.errors import ArtworkError
from src.domain import Artwork, Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectrumArtworkService:
    """Frozen dataclass for managing Spectrum artwork service configuration and operations.

    This service implements the artwork service role by integrating with the Spectrum
    web-to-print platform's HTTP API. The frozen dataclass pattern ensures configuration
    immutability once initialized, with the httpx.Client maintaining connection pooling
    and the digitals_dir path anchoring all downloaded files.

    The client attribute is dynamically set during first API call (get_artwork) using
    object.__setattr__() to bypass frozen state constraints. This captures the clientHandle
    from the Spectrum API response, which is required for subsequent placement PDF requests.

    Attributes:
        engine: Configured httpx.Client with Spectrum API base_url and auth headers.
                Expected base_url format: "https://api.spectrum.example.com/"
        digitals_dir: Path to directory where all artwork files (designs and PDFs) are
                     saved. Directory must exist and be writable.
        client: Dynamic attribute set on first API call, storing the clientHandle from
               Spectrum API response. Used to construct placement PDF URLs.

    Example:
        >>> engine = httpx.Client(
        ...     base_url="https://api.spectrum.example.com/",
        ...     headers={"Authorization": "Bearer token"},
        ... )
        >>> service = SpectrumArtworkService(engine=engine, digitals_dir=Path("/tmp/artwork"))
        >>> artwork_files = service.get_artwork(order)
        >>> len(artwork_files)  # PDF + design files per line item
        42
    """

    engine: httpx.Client
    digitals_dir: Path
    client: str = field(default="", init=False)

    def get_artwork(self, order: Order) -> list[Path]:
        """Retrieve and download all artwork assets for an order from Spectrum.

        Orchestrates the complete artwork retrieval workflow:
        1. Queries Spectrum API for order metadata and line item artwork references
        2. Extracts clientHandle from response (stored as self.client for later use)
        3. Builds set of (sku, quantity, recipeSetId) tuples from API response
        4. Iterates through order line items, matching each to Spectrum artwork by
           product code and quantity
        5. For matched line items, downloads designs (ZIP) and placement PDF
        6. Attaches Artwork object to each line item with URLs and local file paths
        7. Returns complete list of all local file paths for downstream processing

        The matching process is strict: both product code and quantity must match exactly.
        If no matching artwork is found for any line item, raises ArtworkError with line
        item details to prevent incomplete orders from proceeding.

        Args:
            order: Order object with populated line items. Must have valid remote_order_id
                  and sale_id set. Each line item requires product_code, quantity, and
                  remote_line_id attributes.

        Returns:
            List of Path objects for all downloaded files, including design files (from
            ZIP extraction) and placement PDFs. Paths use local digitals_dir location
            with sale ID prefix for traceability (e.g., "S00123_design.pdf").

        Raises:
            ArtworkError: If any order line item has no matching artwork in Spectrum
                         API response based on (product_code, quantity) matching.
                         Error message includes line item details and remote_order_id
                         for diagnostics.
            httpx.HTTPError: If Spectrum API request fails (404, 500, etc.) or
                            network error occurs.

        Example:
            >>> order.remote_order_id = "ORD-12345"
            >>> order.sale_id = 123
            >>> for li in order.line_items:
            ...     li.product_code = "ABC123"
            ...     li.quantity = 5
            ...     li.remote_line_id = "LI-001"
            >>> files = service.get_artwork(order)
            >>> all(f.exists() for f in files)  # All files downloaded
            True
        """
        logger.info(f"Getting artwork IDs for order {order.remote_order_id}")
        endpoint = f"/api/order/order-number/{order.remote_order_id}/"
        response = self.engine.get(url=endpoint)
        response.raise_for_status()
        object.__setattr__(self, "client", response.json().get("clientHandle", ""))

        # build a set of tuples containing the product code, quantity, and recipe set ID
        artwork_data: set[tuple[str, int, str]] = set()
        for li in response.json().get("line_items", []):
            for sku_qty in li.get("skuQuantities", []):
                artwork_data.add((sku_qty["sku"], sku_qty["quantity"], li.get("recipeSetId")))

        file_paths: list[Path] = []
        for li in order.line_items:
            for sku, qty, recipe_set_id in artwork_data:
                if li.product_code == sku and li.quantity == qty:
                    artwork = Artwork(
                        artwork_id=recipe_set_id,
                        line_item_id=li.remote_line_id,
                        design_url=f"{str(self.engine.base_url).rstrip('/')}/api/webtoprint/{recipe_set_id}/",
                        design_paths=self._get_designs(
                            recipe_set_id=recipe_set_id, sale_id=order.sale_id
                        ),
                        placement_url=f"{str(self.engine.base_url).rstrip('/')}/{self.client}/specification/{recipe_set_id}/pdf/",
                        placement_path=self._get_placement(
                            recipe_set_id=recipe_set_id, sale_id=order.sale_id
                        ),
                    )
                    li.set_artwork(artwork)
                    file_paths.extend(artwork.design_paths)
                    file_paths.append(artwork.placement_path)
                    break
            else:
                # if no artwork found for the line item, raise an error
                raise ArtworkError(
                    message=f"No artwork found for line item ({li.product_code}, {li.quantity})",
                    order_id=order.remote_order_id,
                )

        return file_paths

    def _get_designs(self, recipe_set_id: str, sale_id: int) -> list[Path]:
        """Download and extract design files from Spectrum webtoprint endpoint.

        Queries the Spectrum webtoprint API endpoint for a recipe set, which returns
        a ZIP archive containing all design files (typically PDFs or images). The archive
        is extracted directly to digitals_dir with each file renamed to include the
        sale ID prefix for traceability.

        Filename transformation:
        - Original: "design_v1.pdf"
        - Saved as: "S00123_design_v1.pdf" (where 00123 is the 5-digit sale_id)

        This prefix matching allows downstream systems to quickly find all designs
        associated with a specific sale.

        Args:
            recipe_set_id: Spectrum recipe set identifier, obtained from API response.
                          Used to construct endpoint: /api/webtoprint/{recipe_set_id}/
            sale_id: Sale/order ID for filename prefixing in format "S{sale_id:05}"
                    (e.g., S00123 for sale_id=123, S99999 for sale_id=99999).

        Returns:
            List of Path objects for extracted design files. All paths point to files
            in self.digitals_dir with sale ID prefix applied. Order matches ZIP
            member extraction order.

        Raises:
            httpx.HTTPError: If Spectrum API request fails (404, 500, etc.) or
                            network error occurs.
            zipfile.BadZipFile: If response content is not a valid ZIP archive.

        Example:
            >>> designs = service._get_designs(recipe_set_id="RST-456", sale_id=123)
            >>> len(designs)  # Number of files in ZIP
            7
            >>> designs[0].name  # e.g., S00123_cover.pdf
            'S00123_cover.pdf'
        """
        logger.info("Get designs for artwork %s and order %d", recipe_set_id, sale_id)
        endpoint = f"/api/webtoprint/{recipe_set_id}/"
        response = self.engine.get(url=endpoint)
        response.raise_for_status()

        saved_as: list[Path] = []
        with ZipFile(io.BytesIO(response.content)) as zip_file:
            for member in zip_file.infolist():
                # Set filename to include order ID and extract to self.digitals_dir
                member.filename = f"S{sale_id:05}_{member.filename}"
                zip_file.extract(member, path=self.digitals_dir)
                saved_as.append(self.digitals_dir / member.filename)
                logger.debug(f"Extracted {member.filename} to {saved_as[-1]}")

        return saved_as

    def _get_placement(self, recipe_set_id: str, sale_id: int) -> Path:
        """Download placement specification PDF from Spectrum.

        Queries the Spectrum specification endpoint to download the placement PDF,
        which contains production specifications, file setup details, and placement
        guidelines for the artwork. The PDF is saved to digitals_dir with sale ID
        prefix for traceability.

        Endpoint construction uses self.client (clientHandle), which must be set
        from the initial get_artwork() API call. This requirement ensures the client
        context is established before attempting placement retrieval.

        Args:
            recipe_set_id: Spectrum recipe set identifier for which to retrieve
                          placement specifications.
            sale_id: Sale/order ID for filename prefixing in format "S{sale_id:05}"
                    Results in filename like "S00123_RST-456_placement.pdf".

        Returns:
            Path to saved placement PDF file in digitals_dir. Filename follows the
            pattern "S{sale_id:05}_{recipe_set_id}_placement.pdf" to include both
            sale ID for traceability and recipe set ID for identification.

        Raises:
            httpx.HTTPError: If Spectrum API request fails (404, 500, etc.) or
                            network error occurs. Note: 404 is likely if client
                            context (self.client) is not set from get_artwork().

        Example:
            >>> placement = service._get_placement(recipe_set_id="RST-456", sale_id=123)
            >>> placement.name
            'S00123_RST-456_placement.pdf'
            >>> placement.exists()
            True
        """
        logger.info("Get placement for artwork %s and order %d", recipe_set_id, sale_id)
        endpoint = f"/{self.client}/specification/{recipe_set_id}/pdf/"
        response = self.engine.get(url=endpoint)
        response.raise_for_status()
        save_as = self.digitals_dir / f"S{sale_id:05}_{recipe_set_id}_placement.pdf"
        save_as.write_bytes(response.content)
        logger.debug(f"Saved placement PDF to {save_as}")
        return save_as
