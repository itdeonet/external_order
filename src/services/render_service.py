"""Jinja2-based template rendering service.

Provides `RenderService` to load and render templates from a directory with
safe auto-escaping and sensible environment defaults.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import get_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderService:
    """Render templates from `directory` using a configured Jinja2 `Environment`.

    Environment is created in `__post_init__` and configured with autoescape
    and sensible formatting options.
    """

    directory: Path = field(default_factory=lambda: Path(get_config().templates_dir))
    env: Environment = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Create and assign the Jinja2 `Environment`; validate `directory`."""
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
        """Render `template_name` with `data` and return the result string."""
        logger.info(f"Rendering template {template_name}")
        template = self.env.get_template(template_name)
        return template.render(**data)
