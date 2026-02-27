"""Render service for Jinja2 templates."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderService:
    """Renders templates using Jinja2 templates."""

    directory: Path
    env: Environment = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.directory.is_dir():
            raise ValueError(f"Directory {self.directory} does not exist or is not a directory.")
        object.__setattr__(
            self,
            "env",
            Environment(
                loader=FileSystemLoader(str(self.directory)),
                autoescape=select_autoescape(["html", "xml", "txt"]),
                trim_blocks=True,
                lstrip_blocks=True,
            ),
        )

    def render(self, template_name: str, data: dict[str, Any]) -> str:
        """Render a template with the provided data."""
        logger.info(f"Rendering template {template_name}")
        template = self.env.get_template(template_name)
        return template.render(**data)
