"""Unit tests for RenderService."""

from pathlib import Path

import pytest
from jinja2 import Environment

from src.services.render_service import RenderService


class TestRenderServiceInstantiation:
    """Tests for RenderService instantiation."""

    def test_instantiation_with_valid_directory(self, tmp_path):
        """Test creating RenderService with a valid directory."""
        service = RenderService(directory=tmp_path)

        assert service.directory == tmp_path

    def test_instantiation_raises_when_directory_not_exists(self, tmp_path):
        """Test that instantiation raises when directory doesn't exist."""
        non_existent = tmp_path / "non_existent"

        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            RenderService(directory=non_existent)

    def test_instantiation_raises_when_path_is_file(self, tmp_path):
        """Test that instantiation raises when path is a file, not a directory."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            RenderService(directory=file_path)

    def test_directory_is_required_parameter(self, tmp_path):
        """Test that directory is a required parameter."""
        with pytest.raises(TypeError):
            RenderService()  # type: ignore

    def test_instantiation_accepts_path_object(self, tmp_path):
        """Test that instantiation accepts pathlib.Path object."""
        service = RenderService(directory=Path(tmp_path))

        assert isinstance(service.directory, Path)
        assert service.directory == tmp_path


class TestRenderServiceEnvironment:
    """Tests for RenderService Jinja2 environment setup."""

    def test_environment_is_initialized(self, tmp_path):
        """Test that Jinja2 Environment is properly initialized."""
        service = RenderService(directory=tmp_path)

        assert isinstance(service.env, Environment)

    def test_environment_has_autoescape_enabled(self, tmp_path):
        """Test that autoescape is enabled for html and xml files."""
        service = RenderService(directory=tmp_path)

        # Verify autoescape is configured
        assert service.env.autoescape is not None

    def test_environment_trim_blocks_enabled(self, tmp_path):
        """Test that trim_blocks is enabled."""
        service = RenderService(directory=tmp_path)

        assert service.env.trim_blocks is True

    def test_environment_lstrip_blocks_enabled(self, tmp_path):
        """Test that lstrip_blocks is enabled."""
        service = RenderService(directory=tmp_path)

        assert service.env.lstrip_blocks is True

    def test_environment_is_not_in_repr(self, tmp_path):
        """Test that environment field is excluded from repr."""
        service = RenderService(directory=tmp_path)
        repr_str = repr(service)

        assert "env=" not in repr_str
        assert "directory=" in repr_str


class TestRenderMethod:
    """Tests for RenderService render method."""

    @pytest.fixture
    def service(self, tmp_path):
        """Provide a RenderService instance."""
        return RenderService(directory=tmp_path)

    def test_render_simple_template(self, service, tmp_path):
        """Test rendering a simple template without variables."""
        template_content = "Hello, World!"
        template_file = tmp_path / "simple.txt"
        template_file.write_text(template_content)

        result = service.render("simple.txt", {})

        assert result == "Hello, World!"

    def test_render_template_with_variable(self, service, tmp_path):
        """Test rendering template with a single variable."""
        template_content = "Hello, {{ name }}!"
        template_file = tmp_path / "greeting.txt"
        template_file.write_text(template_content)

        result = service.render("greeting.txt", {"name": "Alice"})

        assert result == "Hello, Alice!"

    def test_render_template_with_multiple_variables(self, service, tmp_path):
        """Test rendering template with multiple variables."""
        template_content = "{{ greeting }}, {{ name }}! You are {{ age }} years old."
        template_file = tmp_path / "complex.txt"
        template_file.write_text(template_content)

        data = {"greeting": "Hello", "name": "Bob", "age": 30}
        result = service.render("complex.txt", data)

        assert result == "Hello, Bob! You are 30 years old."

    def test_render_template_with_loop(self, service, tmp_path):
        """Test rendering template with loop structure."""
        template_content = """List:
{% for item in items %}
- {{ item }}
{% endfor %}"""
        template_file = tmp_path / "list.txt"
        template_file.write_text(template_content)

        data = {"items": ["apple", "banana", "cherry"]}
        result = service.render("list.txt", data)

        assert "apple" in result
        assert "banana" in result
        assert "cherry" in result

    def test_render_template_with_conditional(self, service, tmp_path):
        """Test rendering template with conditional statement."""
        template_content = """{% if is_admin %}
Admin section
{% else %}
User section
{% endif %}"""
        template_file = tmp_path / "conditional.txt"
        template_file.write_text(template_content)

        result_admin = service.render("conditional.txt", {"is_admin": True})
        result_user = service.render("conditional.txt", {"is_admin": False})

        assert "Admin section" in result_admin
        assert "User section" in result_user

    def test_render_template_trims_blocks(self, service, tmp_path):
        """Test that trim_blocks removes block tags from output."""
        template_content = """Line 1
{% for i in range(3) %}
Item {{ i }}
{% endfor %}
Line 2"""
        template_file = tmp_path / "trim.txt"
        template_file.write_text(template_content)

        result = service.render("trim.txt", {})

        # With trim_blocks=True, the output should not have extra newlines from block tags
        assert "Item 0" in result
        assert "Item 1" in result
        assert "Item 2" in result

    def test_render_with_nested_directory(self, service, tmp_path):
        """Test rendering template from a subdirectory."""
        subdir = tmp_path / "templates"
        subdir.mkdir()
        template_file = subdir / "nested.txt"
        template_file.write_text("Nested template")

        result = service.render("templates/nested.txt", {})

        assert result == "Nested template"

    def test_render_returns_string(self, service, tmp_path):
        """Test that render method returns a string."""
        template_file = tmp_path / "test.txt"
        template_file.write_text("{{ value }}")

        result = service.render("test.txt", {"value": "Hello"})

        assert isinstance(result, str)

    def test_render_with_empty_data_dict(self, service, tmp_path):
        """Test rendering with empty data dictionary."""
        template_file = tmp_path / "empty.txt"
        template_file.write_text("Static content")

        result = service.render("empty.txt", {})

        assert result == "Static content"

    def test_render_raises_when_template_not_found(self, service):
        """Test that render raises when template file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            service.render("nonexistent.txt", {})

    def test_render_with_filters(self, service, tmp_path):
        """Test rendering template with Jinja2 filters."""
        template_content = "{{ text | upper }}"
        template_file = tmp_path / "filter.txt"
        template_file.write_text(template_content)

        result = service.render("filter.txt", {"text": "hello"})

        assert result == "HELLO"

    def test_render_with_dict_variable(self, service, tmp_path):
        """Test rendering with dictionary variable."""
        template_content = "{{ user.name }} is {{ user.age }} years old"
        template_file = tmp_path / "dict.txt"
        template_file.write_text(template_content)

        data = {"user": {"name": "Alice", "age": 25}}
        result = service.render("dict.txt", data)

        assert result == "Alice is 25 years old"

    def test_render_with_list_variable(self, service, tmp_path):
        """Test rendering with list variable."""
        template_content = "First: {{ items[0] }}, Last: {{ items[-1] }}"
        template_file = tmp_path / "list_access.txt"
        template_file.write_text(template_content)

        data = {"items": ["a", "b", "c"]}
        result = service.render("list_access.txt", data)

        assert result == "First: a, Last: c"

    def test_render_logs_template_path(self, service, tmp_path, mocker, caplog):
        """Test that render logs the template path."""
        import logging

        with caplog.at_level(logging.INFO):
            template_file = tmp_path / "logged.txt"
            template_file.write_text("Test")

            service.render("logged.txt", {})

            assert f"Rendering template {tmp_path / 'logged.txt'}" in caplog.text

    def test_render_with_special_characters(self, service, tmp_path):
        """Test rendering with special characters."""
        template_content = "{{ text }}"
        template_file = tmp_path / "special.txt"
        template_file.write_text(template_content)

        data = {"text": "Hello & goodbye < > ' \""}
        result = service.render("special.txt", data)

        # Autoescape is enabled, so special characters are HTML-escaped
        assert "Hello &amp; goodbye &lt; &gt; &#39; &#34;" in result

    def test_render_preserves_whitespace_with_lstrip(self, service, tmp_path):
        """Test that lstrip_blocks is applied correctly."""
        template_content = """Start
  {% if true %}
  Content
  {% endif %}
End"""
        template_file = tmp_path / "whitespace.txt"
        template_file.write_text(template_content)

        result = service.render("whitespace.txt", {})

        # With lstrip_blocks=True, leading whitespace should be stripped
        assert "Start" in result
        assert "Content" in result
        assert "End" in result


class TestRenderServiceImmutability:
    """Tests for RenderService immutability (frozen dataclass)."""

    def test_cannot_modify_directory(self, tmp_path):
        """Test that directory cannot be modified."""
        service = RenderService(directory=tmp_path)

        with pytest.raises((AttributeError, TypeError)):
            service.directory = tmp_path / "other"  # type: ignore

    def test_cannot_modify_env(self, tmp_path):
        """Test that env cannot be modified."""
        service = RenderService(directory=tmp_path)
        new_env = Environment()

        with pytest.raises((AttributeError, TypeError)):
            service.env = new_env  # type: ignore

    def test_cannot_add_new_attributes(self, tmp_path):
        """Test that new attributes cannot be added to frozen dataclass."""
        service = RenderService(directory=tmp_path)

        with pytest.raises((AttributeError, TypeError)):
            service.new_attribute = "value"  # type: ignore


class TestRenderServiceIntegration:
    """Integration tests for RenderService."""

    def test_render_multiple_templates_in_sequence(self, tmp_path):
        """Test rendering multiple different templates."""
        service = RenderService(directory=tmp_path)

        # Create multiple templates
        (tmp_path / "template1.txt").write_text("Template 1: {{ value }}")
        (tmp_path / "template2.txt").write_text("Template 2: {{ value | upper }}")
        (tmp_path / "template3.txt").write_text(
            "Template 3: {% for i in items %}{{ i }} {% endfor %}"
        )

        result1 = service.render("template1.txt", {"value": "hello"})
        result2 = service.render("template2.txt", {"value": "hello"})
        result3 = service.render("template3.txt", {"items": [1, 2, 3]})

        assert result1 == "Template 1: hello"
        assert result2 == "Template 2: HELLO"
        assert "Template 3: 1 2 3" in result3

    def test_render_reuses_same_environment(self, tmp_path):
        """Test that multiple renders reuse the same Jinja2 environment."""
        service = RenderService(directory=tmp_path)
        (tmp_path / "test.txt").write_text("{{ value }}")

        env_before = service.env
        service.render("test.txt", {"value": "test1"})
        service.render("test.txt", {"value": "test2"})
        env_after = service.env

        # Environment should be the same object throughout
        assert env_before is env_after

    def test_render_with_complex_nested_data(self, tmp_path):
        """Test rendering with complex nested data structures."""
        service = RenderService(directory=tmp_path)

        template_content = """Company: {{ company.name }}
Employees:
{% for emp in company.employees %}
  - {{ emp.name }}: {{ emp.role }}
{% endfor %}"""

        (tmp_path / "company.txt").write_text(template_content)

        data = {
            "company": {
                "name": "TechCorp",
                "employees": [
                    {"name": "Alice", "role": "Engineer"},
                    {"name": "Bob", "role": "Manager"},
                ],
            }
        }

        result = service.render("company.txt", data)

        assert "TechCorp" in result
        assert "Alice" in result
        assert "Engineer" in result
        assert "Bob" in result
        assert "Manager" in result

    def test_render_with_inline_conditional_logic(self, tmp_path):
        """Test rendering with conditional expressions."""
        service = RenderService(directory=tmp_path)

        template_content = "{{ 'adult' if age >= 18 else 'minor' }}"
        (tmp_path / "age_check.txt").write_text(template_content)

        result_adult = service.render("age_check.txt", {"age": 25})
        result_minor = service.render("age_check.txt", {"age": 15})

        assert result_adult.strip() == "adult"
        assert result_minor.strip() == "minor"
