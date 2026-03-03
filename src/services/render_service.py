"""Template rendering service using Jinja2.

This module provides the RenderService class, which wraps Jinja2's template
rendering functionality. It handles template discovery, environment configuration,
and rendering with proper escaping for HTML, XML, and text content.

The service is used to generate EDI messages, email content, and other formatted
output from templates and data.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderService:
    """Template rendering service using Jinja2 environment.

    This service wraps Jinja2 to provide consistent template rendering with
    proper escaping and formatting. Templates are loaded from the specified
    directory and rendered with provided data dictionaries.

    The service automatically configures Jinja2 with:
    - File system template loader pointing to the directory
    - Auto-escape enabled for HTML, XML, and text files
    - Block trimming and left-side stripping for cleaner output

    This class enforces:
    - Frozen: All attributes are read-only after creation
    - Lazy initialization: Jinja2 Environment created in __post_init__
    - Directory validation: Directory must exist before use

    Attributes:
        directory: Path to directory containing template files (.j2 or others)
        env: Jinja2 Environment instance (created during __post_init__)

    Example:
        >>> from pathlib import Path
        >>> service = RenderService(directory=Path("src/templates"))
        >>> html = service.render("notification.html.j2", {"user": "Alice"})
        >>> txt = service.render("message.txt.j2", {"subject": "Hello"})
    """

    directory: Path
    env: Environment = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize Jinja2 environment with directory and escaping settings.

        Sets up the Jinja2 Environment after dataclass initialization, configuring:
        - FileSystemLoader to load templates from the directory
        - Auto-escape for safe rendering of HTML, XML, and text content
        - Block trimming and left-side stripping for clean output formatting

        Raises:
            ValueError: If directory does not exist or is not a directory
        """
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
        """Render a Jinja2 template with the provided data.

        Loads the template by name from the configured directory and renders it
        with the given data dictionary. Auto-escaping is applied based on file
        extension for security.

        Args:
            template_name: Name of the template file (e.g., 'message.html.j2')
            data: Dictionary of variables to make available to the template

        Returns:
            Rendered template as a string

        Raises:
            jinja2.TemplateNotFound: If template file is not found in directory
            jinja2.TemplateError: If template rendering fails (syntax, undefined vars, etc)
        """
        logger.info(f"Rendering template {template_name}")
        template = self.env.get_template(template_name)
        return template.render(**data)
