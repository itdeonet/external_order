"""Spectrum artwork service for retrieving and managing digital assets from Spectrum API."""

import io
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from zipfile import ZipFile

import requests

from src.app.errors import ArtworkError
from src.config import get_config
from src.domain import Artwork, Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectrumArtworkService:
    """Retrieve and download digital artwork assets from Spectrum API.

    Attributes:
        session: requests.Session configured with auth headers.
        base_url: Spectrum API base URL (e.g., "https://api.spectrum.example.com/").
        digitals_dir: Directory where downloaded artwork files are saved.
        client: Spectrum clientHandle, set from first API call.
    """

    session: requests.Session
    base_url: str = field(default_factory=lambda: get_config().spectrum_base_url)
    digitals_dir: Path = field(default_factory=lambda: Path(get_config().digitals_dir))
    client_handle: str = field(default="", init=False)

    def __post_init__(self) -> None:
        """post init to ensure the object is valid."""
        self.session.headers.update({"SPECTRUM_API_TOKEN": get_config().spectrum_api_key})

    def get_artwork(self, order: Order) -> list[Path]:
        """Retrieve and download artwork assets for an order.

        Queries Spectrum API for order artwork metadata, matches to line items by product code
        and quantity, downloads design files and placement PDFs, and returns all file paths.

        Args:
            order: Order with line_items. Must have remote_order_id and sale_id set.

        Returns:
            List of Path objects for downloaded files (prefixed with sale ID).

        Raises:
            ArtworkError: If any line item has no matching artwork in Spectrum.
            requests.exceptions.RequestException: If API request fails.
        """
        logger.info(f"Getting artwork IDs for order {order.remote_order_id}")
        endpoint = f"/api/order/order-number/{order.remote_order_id}/"
        response = self.session.get(url=f"{self.base_url.rstrip('/')}{endpoint}", timeout=(5, 30))
        response.raise_for_status()
        object.__setattr__(self, "client_handle", response.json().get("clientHandle", ""))

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
                        line_id=li.line_id,
                        design_url=f"{self.base_url.rstrip('/')}/api/webtoprint/{recipe_set_id}/",
                        design_paths=self._get_designs(
                            recipe_set_id=recipe_set_id, sale_id=order.sale_id
                        ),
                        placement_url=f"{self.base_url.rstrip('/')}/{self.client_handle}/specification/{recipe_set_id}/pdf/",
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
        """Download and extract design files from Spectrum.

        Queries webtoprint endpoint for recipe set, extracts ZIP contents to digitals_dir
        with sale ID prefix (S{sale_id:05}_{filename}).

        Args:
            recipe_set_id: Spectrum recipe set identifier.
            sale_id: Sale ID for filename prefix.

        Returns:
            List of Path objects for extracted design files.

        Raises:
            requests.exceptions.RequestException: If API request fails.
        """
        logger.info("Get designs for artwork %s and order %d", recipe_set_id, sale_id)
        endpoint = f"/api/webtoprint/{recipe_set_id}/"
        response = self.session.get(url=f"{self.base_url.rstrip('/')}{endpoint}", timeout=(5, 30))
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

        Saves PDF to digitals_dir with filename format: S{sale_id:05}_{recipe_set_id}_placement.pdf

        Args:
            recipe_set_id: Spectrum recipe set identifier.
            sale_id: Sale ID for filename prefix.

        Returns:
            Path to saved placement PDF file.

        Raises:
            requests.exceptions.RequestException: If API request fails.
        """
        logger.info("Get placement for artwork %s and order %d", recipe_set_id, sale_id)
        endpoint = f"/{self.client_handle}/specification/{recipe_set_id}/pdf/"
        response = self.session.get(url=f"{self.base_url.rstrip('/')}{endpoint}", timeout=(5, 30))
        response.raise_for_status()
        save_as = self.digitals_dir / f"S{sale_id:05}_{recipe_set_id}_placement.pdf"
        save_as.write_bytes(response.content)
        logger.debug(f"Saved placement PDF to {save_as}")
        return save_as
