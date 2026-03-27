"""Pre-Production Service Module"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf

from src.config import get_config
from src.domain import Order

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class PreProductionService:
    """Pre-Production Service Class"""

    pre_production_data: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        """Initialize Pre-Production Service"""
        pre_production_data_file = get_config().pre_production_data_file
        pre_production_data: dict[str, Any] = json.loads(pre_production_data_file.read_text())
        object.__setattr__(self, "pre_production_data", pre_production_data)

    def create_batch_pdf(self, order: Order) -> list[Path]:
        """Create batch PDF files for the given order based on the pre-production data."""
        logger.info("Creating batch PDF files for order %s", order.remote_order_id)
        saved_files: list[Path] = []
        for li in order.line_items:
            product_data = self.pre_production_data.get(li.product_code, {})
            batch_size = product_data.get("batch_size", 1)
            if not li.artwork:
                logger.warning(
                    "Skipping line item %s (%s) due to missing artwork", li.line_id, li.product_code
                )
                continue

            for design_path in li.artwork.design_paths:
                # RGB pixmap with 300 DPI resolution and 1:1 scale
                pix = pymupdf.Pixmap(design_path)
                if pix.colorspace and pix.colorspace.name != pymupdf.csRGB.name:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                pix.set_dpi(300, 300)

                assert isinstance(pix.width, int) and isinstance(pix.height, int)
                points_width = int(pix.width) * 72 / 300
                points_height = int(pix.height) * 72 / 300
                target_rect = pymupdf.Rect(0, 0, points_width, points_height)

                for idx in range(0, li.quantity, batch_size):
                    doc: pymupdf.Document = pymupdf.open()
                    batch_quantity = min(batch_size, li.quantity - idx)
                    batch_number: int = (idx // batch_size) + 1
                    partial_order_name: str = design_path.stem.split("_")[0][-4:]
                    file_path = self._get_batch_path(
                        design_path, product_data, partial_order_name, batch_number
                    )

                    for _ in range(batch_quantity):
                        page = doc.new_page(width=points_width, height=points_height)
                        page.insert_image(target_rect, pixmap=pix)

                    doc.save(file_path)
                    saved_files.append(file_path)
                    doc.close()
                    logger.info("Saved batch file: %s", file_path)

        return saved_files

    def _get_batch_path(
        self,
        design_path: Path,
        product_data: dict[str, Any],
        partial_order_name: str,
        batch_number: int,
    ) -> Path:
        """Get the batch file path based on the design path and product data"""
        pre_production_dir = get_config().pre_production_dir
        if "upper" in design_path.stem.lower():
            directory = pre_production_dir / product_data.get("directory_upper", "")
            directory.mkdir(parents=True, exist_ok=True)
            return directory / f"_{partial_order_name}_{batch_number}_upper.pdf"
        elif "lower" in design_path.stem.lower():
            directory = pre_production_dir / product_data.get("directory_lower", "")
            directory.mkdir(parents=True, exist_ok=True)
            return directory / f"_{partial_order_name}_{batch_number}_lower.pdf"
        else:
            directory = pre_production_dir / product_data.get("directory", "")
            directory.mkdir(parents=True, exist_ok=True)
            return directory / f"_{partial_order_name}_{batch_number}.pdf"


"""
1. document with tiff -> pdf images, as many pages as belong to the order
2. untoched placement file
3. upload to quite
4. wait for quite to finish and add last for digits or order number to pdf file
5. print the pdf file
"""
