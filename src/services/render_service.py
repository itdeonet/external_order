"""Render service for Jinja2 templates."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, Template, select_autoescape

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
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            ),
        )

    def render(self, template_name: str, data: dict) -> str:
        """Render a template with the provided data."""
        template_path: Path = self.directory / template_name
        logger.info("Rendering template %s", template_path)
        content: str = template_path.read_text()
        template: Template = self.env.from_string(content)
        return template.render(**data)
