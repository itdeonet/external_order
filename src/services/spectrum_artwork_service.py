"""Spectrum artwork service implementation."""

import io
from logging import getLogger
from pathlib import Path
from zipfile import ZipFile

import httpx

from src.domain.order import Order

logger = getLogger(__name__)


class SpectrumArtworkService:
    """Spectrum artwork service implementation."""

    def __init__(self, engine: httpx.Client, digitals_dir: Path) -> None:
        """Initialize the service."""
        self._engine = engine
        self._digitals_dir = digitals_dir
        self._client = ""

    def get_artwork(self, order: Order) -> list[Path]:
        """Get artwork data for the given remote ID."""
        return self._get_designs(order) + self._get_placements(order)

    def get_artwork_ids(self, order: Order) -> None:
        """Get artwork IDs for the given remote ID."""
        logger.info(f"Getting artwork IDs for order {order.remote_order_id}")
        endpoint = f"/api/order/order-number/{order.remote_order_id}/"
        response = self._engine.get(url=endpoint)
        response.raise_for_status()
        self._client = response.json().get("clientHandle", "")

        artwork_data = {
            (sku_qty["sku"], sku_qty["quantity"]): item.get("recipeSetId")
            for item in response.json().get("line_items", [])
            for sku_qty in item.get("skuQuantities", [])
        }

        # Match artwork IDs to line items based on product ID and quantity
        # The additional quantities are a workaround for the +1 quantity issue in the Harman orders
        for key, value in artwork_data.items():
            if li := next(
                (
                    li
                    for li in order.line_items
                    if li.product_id == key[0] and li.quantity in (key[1], key[1] - 1, 1)
                ),
                None,
            ):
                li.set_artwork_id(value)

    def _get_designs(self, order: Order) -> list[Path]:
        """Get designs for the given remote ID."""
        logger.info(f"Get designs for order {order.remote_order_id}")
        saved_paths: list[Path] = []

        for line_item in order.line_items:
            if not line_item.artwork_id:
                continue

            endpoint = f"/api/webtoprint/{line_item.artwork_id}/"
            response = self._engine.get(url=endpoint)
            response.raise_for_status()

            saved_as: list[Path] = []
            with ZipFile(io.BytesIO(response.content)) as zip_file:
                for member in zip_file.infolist():
                    # Set filename to include order ID and extract to self._digitals_dir
                    member.filename = f"S{order.id:05}_{member.filename}"
                    zip_file.extract(member, path=self._digitals_dir)
                    saved_as.append(self._digitals_dir / member.filename)

            line_item.set_design(
                url=f"{str(self._engine.base_url).rstrip('/')}{endpoint}", paths=saved_as
            )
            saved_paths.extend(saved_as)

        return saved_paths

    def _get_placements(self, order: Order) -> list[Path]:
        """Get placements for the given remote ID."""
        logger.info(f"Get placements for order {order.remote_order_id}")
        saved_paths: list[Path] = []

        for line_item in order.line_items:
            if not line_item.artwork_id:
                continue

            endpoint = f"/{self._client}/specification/{line_item.artwork_id}/pdf/"
            response = self._engine.get(url=endpoint)
            response.raise_for_status()
            saved_as = self._digitals_dir / f"S{order.id:05}_{line_item.artwork_id}_placement.pdf"
            saved_as.write_bytes(response.content)

            line_item.set_placement(
                url=f"{str(self._engine.base_url).rstrip('/')}{endpoint}", path=saved_as
            )
            saved_paths.append(saved_as)

        return saved_paths
