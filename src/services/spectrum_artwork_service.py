"""Spectrum artwork service implementation."""

import io
from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from zipfile import ZipFile

import httpx

from src.app.errors import ArtworkError
from src.domain.artwork import Artwork
from src.domain.order import Order

logger = getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class SpectrumArtworkService:
    """Spectrum artwork service implementation."""

    engine: httpx.Client
    digitals_dir: Path
    client: str = field(default="", init=False)

    def get_artwork(self, order: Order) -> list[Path]:
        """Get artwork for the given order."""
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
        """Get designs for the given endpoint and order ID."""
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
        """Get placement for the given endpoint and order ID."""
        logger.info("Get placement for artwork %s and order %d", recipe_set_id, sale_id)
        endpoint = f"/{self.client}/specification/{recipe_set_id}/pdf/"
        response = self.engine.get(url=endpoint)
        response.raise_for_status()
        save_as = self.digitals_dir / f"S{sale_id:05}_{recipe_set_id}_placement.pdf"
        save_as.write_bytes(response.content)
        logger.debug(f"Saved placement PDF to {save_as}")
        return save_as
