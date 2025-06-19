"""Tests for llm-templates-latitude plugin"""

from unittest.mock import Mock, patch

import pytest

from llm_templates_latitude import latitude_template_loader
from utils import extract_template_data, is_uuid_like, parse_template_path


def test_template_loader_registration():
    """Test that the template loader is properly registered"""
    # Import should register the template loader
    import llm_templates_latitude

    # Check if the loader is registered (this would need to be tested with actual LLM)
    # For now, just verify the function exists
    assert hasattr(llm_templates_latitude, "latitude_template_loader")
    assert callable(llm_templates_latitude.latitude_template_loader)


def test_parse_template_path():
    """Test parsing of template paths"""
    # Test with project_id/version_uuid/document_path format
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    project_id, version_uuid, document_path = parse_template_path(
        f"12345/{test_uuid}/email-template"
    )
    assert project_id == "12345"
    assert version_uuid == test_uuid
    assert document_path == "email-template"

    # Test with version_uuid/document_path format
    project_id, version_uuid, document_path = parse_template_path(
        f"{test_uuid}/welcome-email"
    )
    assert project_id is None
    assert version_uuid == test_uuid
    assert document_path == "welcome-email"

    # Test with project_id/live/document_path format
    project_id, version_uuid, document_path = parse_template_path(
        "12345/live/email-template"
    )
    assert project_id == "12345"
    assert version_uuid == "live"
    assert document_path == "email-template"


def test_is_uuid_like():
    """Test UUID detection"""
    # Valid UUIDs
    assert is_uuid_like("550e8400-e29b-41d4-a716-446655440000") is True
    assert is_uuid_like("6ba7b810-9dad-11d1-80b4-00c04fd430c8") is True
    assert is_uuid_like("6BA7B810-9DAD-11D1-80B4-00C04FD430C8") is True  # uppercase

    # Invalid UUIDs
    assert is_uuid_like("not-a-uuid") is False
    assert is_uuid_like("550e8400-e29b-41d4-a716") is False  # too short
    assert (
        is_uuid_like("550e8400-e29b-41d4-a716-446655440000-extra") is False
    )  # too long
    assert is_uuid_like("marketing/email-template") is False


def test_extract_template_data():
    """Test template data extraction"""
    # Test with full data
    latitude_data = {
        "content": "Hello {{name}}",
        "system": "You are helpful",
        "model": "gpt-4",
        "parameters": {"name": "User"},
        "model_config": {"temperature": 0.8},
        "schema": {"type": "object"},
    }

    config = extract_template_data(latitude_data)

    assert config["prompt"] == "Hello $name"  # Variables converted from {{}} to $
    assert config["system"] == "You are helpful"
    assert "model" not in config  # Model is now filtered out
    assert config["defaults"] == {"name": "User"}
    assert config["options"] == {"temperature": 0.8}
    assert config["schema_object"] == {"type": "object"}

    # Test with minimal data
    minimal_data = {"content": "Hello world"}
    config = extract_template_data(minimal_data)
    assert config["prompt"] == "Hello world"
    assert "system" not in config
    assert "model" not in config  # Model is never included now


def test_latitude_template_loader_integration():
    """Test integration of template loader components"""
    # This test verifies the integration without mocking the HTTP layer
    # The actual API calls are tested in test_lat.py

    # Test that the function exists and can parse paths correctly
    from utils import extract_template_data, parse_template_path

    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    project_id, version_uuid, document_path = parse_template_path(
        f"99999/{test_uuid}/welcome-email"
    )

    assert project_id == "99999"
    assert version_uuid == test_uuid
    assert document_path == "welcome-email"

    # Test template data extraction
    mock_data = {
        "content": "Hello {{name}}",
        "system": "You are helpful",
        "model": "gpt-4",
    }

    config = extract_template_data(mock_data)
    assert config["prompt"] == "Hello $name"  # Variables converted from {{}} to $
    assert config["system"] == "You are helpful"
    assert "model" not in config  # Model is now filtered out


@patch("llm_templates_latitude.os.getenv")
def test_get_api_key_from_env(mock_getenv):
    """Test getting API key from environment variable"""
    from llm_templates_latitude import _get_api_key

    mock_getenv.return_value = "env-api-key"

    api_key = _get_api_key()
    assert api_key == "env-api-key"
    mock_getenv.assert_called_with("LATITUDE_API_KEY")


@patch("llm_templates_latitude.llm.get_key")
@patch("llm_templates_latitude.os.getenv")
def test_get_api_key_missing(mock_getenv, mock_get_key):
    """Test error when API key is missing"""
    from llm_templates_latitude import _get_api_key

    mock_getenv.return_value = None
    mock_get_key.side_effect = Exception("Key not found")

    with pytest.raises(ValueError, match="Latitude API key not found"):
        _get_api_key()


class TestPrefixBasedSelection:
    """Test template prefix-based client selection functionality"""

    def test_get_client_implementation_http_prefixes(self):
        """Test that HTTP client is used for lat and lat-http prefixes"""
        from llm_templates_latitude import get_client_implementation

        assert get_client_implementation("lat") == "http"
        assert get_client_implementation("lat-http") == "http"

    def test_get_client_implementation_sdk_prefix(self):
        """Test that SDK client is used for lat-sdk prefix"""
        from llm_templates_latitude import get_client_implementation

        assert get_client_implementation("lat-sdk") == "sdk"

    @patch("llm_templates_latitude._get_api_key")
    @patch("lat.LatitudeClient")
    def test_latitude_template_loader_http_explicit(
        self, mock_http_client, mock_get_api_key
    ):
        """Test that HTTP client is used when use_sdk=False"""
        from llm_templates_latitude import latitude_template_loader

        mock_get_api_key.return_value = "test-api-key"
        mock_client = Mock()
        mock_http_client.return_value = mock_client
        mock_client.get_document.return_value = {"content": "Test prompt"}

        # Call with use_sdk=False (HTTP)
        template = latitude_template_loader(
            "12345/550e8400-e29b-41d4-a716-446655440000/test", use_sdk=False
        )

        # Verify HTTP client was instantiated
        mock_http_client.assert_called_once_with("test-api-key")
        assert template.prompt == "Test prompt"

    @patch("llm_templates_latitude._get_api_key")
    def test_latitude_template_loader_sdk_not_available(self, mock_get_api_key):
        """Test that error is raised when SDK is requested but not available"""
        from llm_templates_latitude import latitude_template_loader

        mock_get_api_key.return_value = "test-api-key"

        # Mock the SDK import to fail by patching the specific import
        with patch.dict("sys.modules", {"lat_sdk": None}):
            # Call with use_sdk=True but SDK not available
            with pytest.raises(ValueError, match="SDK not available"):
                latitude_template_loader(
                    "12345/550e8400-e29b-41d4-a716-446655440000/test", use_sdk=True
                )


class TestTemplateLoaderIntegration:
    """Integration tests for template loader functionality"""

    @patch("lat.LatitudeClient")
    @patch("llm_templates_latitude._get_api_key")
    def test_latitude_template_loader_success(
        self, mock_get_api_key, mock_client_class
    ):
        """Test successful template loading with HTTP client"""
        mock_get_api_key.return_value = "test-api-key"

        # Setup mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_document.return_value = {
            "content": "Hello {{name}}, how are you?",
            "system": "You are a helpful assistant",
            "parameters": {"name": "User"},
            "model_config": {"temperature": 0.7},
        }

        # Load template using HTTP client (use_sdk=False)
        template = latitude_template_loader(
            "12345/550e8400-e29b-41d4-a716-446655440000/greeting", use_sdk=False
        )

        # Verify template properties
        assert template.prompt == "Hello $name, how are you?"  # Variables converted
        assert template.system == "You are a helpful assistant"
        assert template.defaults == {"name": "User"}
        assert template.options == {"temperature": 0.7}
        assert template.name == "12345/550e8400-e29b-41d4-a716-446655440000/greeting"

    @patch("lat.LatitudeClient")
    @patch("llm_templates_latitude._get_api_key")
    def test_latitude_template_loader_with_frontmatter(
        self, mock_get_api_key, mock_client_class
    ):
        """Test template loading with frontmatter in content"""
        mock_get_api_key.return_value = "test-api-key"

        # Setup mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_document.return_value = {
            "content": "---\nprovider: openai\nmodel: gpt-4\n---\n\nActual prompt here",
            "parameters": {},
        }

        # Load template using HTTP client
        template = latitude_template_loader(
            "12345/550e8400-e29b-41d4-a716-446655440000/test", use_sdk=False
        )

        # Verify frontmatter is handled correctly
        assert template.prompt == "Actual prompt here"
        assert hasattr(template, "name")
        assert template.name == "12345/550e8400-e29b-41d4-a716-446655440000/test"

    @patch("lat.LatitudeClient")
    @patch("llm_templates_latitude._get_api_key")
    def test_latitude_template_loader_authentication_error(
        self, mock_get_api_key, mock_client_class
    ):
        """Test authentication error handling"""
        from lat import LatitudeAuthenticationError

        mock_get_api_key.return_value = "test-api-key"

        # Setup mock client to raise auth error
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_document.side_effect = LatitudeAuthenticationError(
            "Invalid API key"
        )

        # Should raise ValueError with auth error message
        with pytest.raises(ValueError, match="Authentication error"):
            latitude_template_loader(
                "12345/550e8400-e29b-41d4-a716-446655440000/test", use_sdk=False
            )

    @patch("lat.LatitudeClient")
    @patch("llm_templates_latitude._get_api_key")
    def test_latitude_template_loader_not_found_error(
        self, mock_get_api_key, mock_client_class
    ):
        """Test not found error handling"""
        from lat import LatitudeNotFoundError

        mock_get_api_key.return_value = "test-api-key"

        # Setup mock client to raise not found error
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.get_document.side_effect = LatitudeNotFoundError(
            "Document not found"
        )

        # Should raise ValueError with not found message
        with pytest.raises(ValueError, match="Not found"):
            latitude_template_loader(
                "12345/550e8400-e29b-41d4-a716-446655440000/missing-doc", use_sdk=False
            )

    @patch("llm_templates_latitude._get_api_key")
    def test_latitude_template_loader_missing_project_id(self, mock_get_api_key):
        """Test error when project ID is missing for document access"""
        mock_get_api_key.return_value = "test-api-key"

        # Should raise ValueError for invalid format (UUID alone with document name is invalid)
        with pytest.raises(ValueError, match="Project ID is required"):
            latitude_template_loader(
                "550e8400-e29b-41d4-a716-446655440000/document-name", use_sdk=False
            )

    @patch("llm_templates_latitude._get_api_key")
    def test_placeholder_method(self, mock_get_api_key):
        """Placeholder method to fix indentation"""
        pass


class TestFieldFiltering:
    """Test field filtering to avoid 'Extra inputs are not permitted' errors"""

    def test_extract_template_data_filters_model_provider(self):
        """Test that model and provider fields are filtered out"""
        latitude_data = {
            "content": "Test prompt",
            "system": "System prompt",
            "model": "gpt-4",  # Should be filtered
            "provider": "openai",  # Should be filtered
            "parameters": {"key": "value"},
            "model_config": {
                "temperature": 0.8,
                "model": "gpt-4",  # Should be filtered from options
                "provider": "openai",  # Should be filtered from options
            },
        }

        result = extract_template_data(latitude_data)

        # Verify top-level filtering
        assert "model" not in result
        assert "provider" not in result

        # Verify options filtering
        assert "options" in result
        assert "temperature" in result["options"]
        assert "model" not in result["options"]
        assert "provider" not in result["options"]

    def test_extract_template_data_preserves_valid_fields(self):
        """Test that valid fields are preserved during filtering"""
        latitude_data = {
            "content": "Test prompt",
            "system": "System prompt",
            "parameters": {"name": "User", "age": 25},
            "model_config": {
                "temperature": 0.8,
                "max_tokens": 1000,
                "top_p": 0.95,
                "frequency_penalty": 0.5,
            },
            "schema": {"type": "object", "properties": {}},
        }

        result = extract_template_data(latitude_data)

        # Verify all valid fields are preserved
        assert result["prompt"] == "Test prompt"
        assert result["system"] == "System prompt"
        assert result["defaults"] == {"name": "User", "age": 25}
        assert result["options"]["temperature"] == 0.8
        assert result["options"]["max_tokens"] == 1000
        assert result["options"]["top_p"] == 0.95
        assert result["options"]["frequency_penalty"] == 0.5
        assert result["schema_object"]["type"] == "object"


class TestFrontmatterParsing:
    """Test YAML frontmatter parsing in prompts"""

    def test_extract_template_data_with_simple_frontmatter(self):
        """Test simple frontmatter removal"""
        latitude_data = {"content": "---\nmodel: gpt-4\n---\n\nActual content"}

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Actual content"

    def test_extract_template_data_with_complex_frontmatter(self):
        """Test complex frontmatter removal"""
        latitude_data = {
            "content": """---
provider: openai
model: gpt-4
config:
  temperature: 0.8
metadata:
  author: test
---

Multi-line
prompt content
here"""
        }

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Multi-line\nprompt content\nhere"

    def test_extract_template_data_with_no_frontmatter(self):
        """Test content without frontmatter is unchanged"""
        latitude_data = {"content": "This is just regular content\nwith multiple lines"}

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "This is just regular content\nwith multiple lines"

    def test_extract_template_data_with_malformed_frontmatter(self):
        """Test malformed frontmatter is kept as content"""
        latitude_data = {
            "content": "---\nmodel: gpt-4\nThis line breaks YAML\nNo closing ---"
        }

        result = extract_template_data(latitude_data)
        # Should keep original since frontmatter is malformed
        assert "---" in result["prompt"]
        assert "model: gpt-4" in result["prompt"]


class TestVariableConversion:
    """Test conversion of Latitude {{variable}} syntax to LLM $variable syntax"""

    def test_convert_single_variable(self):
        """Test conversion of single variable"""
        latitude_data = {"content": "Hello {{name}}, how are you?"}

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Hello $name, how are you?"

    def test_convert_multiple_variables(self):
        """Test conversion of multiple variables"""
        latitude_data = {
            "content": "Generate a number between {{min}} and {{max}} for {{user}}"
        }

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Generate a number between $min and $max for $user"

    def test_convert_variables_in_system_prompt(self):
        """Test conversion of variables in system prompt"""
        latitude_data = {
            "content": "Main prompt",
            "system": "You are a {{role}} assistant for {{company}}",
        }

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Main prompt"
        assert result["system"] == "You are a $role assistant for $company"

    def test_convert_complex_variables(self):
        """Test conversion with complex variable names"""
        latitude_data = {
            "content": "Process {{user_name}} and {{item_count}} items",
            "system": "Handle {{max_tokens}} tokens",
        }

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Process $user_name and $item_count items"
        assert result["system"] == "Handle $max_tokens tokens"

    def test_no_variables_unchanged(self):
        """Test that content without variables is unchanged"""
        latitude_data = {
            "content": "This has no variables",
            "system": "Neither does this",
        }

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "This has no variables"
        assert result["system"] == "Neither does this"

    def test_mixed_content_with_variables(self):
        """Test content with both variables and regular braces"""
        latitude_data = {
            "content": 'Hello {{name}}! Here\'s some JSON: {"key": "value"} and {{another_var}}'
        }

        result = extract_template_data(latitude_data)
        # Should convert {{name}} and {{another_var}} but leave JSON alone
        assert (
            result["prompt"]
            == 'Hello $name! Here\'s some JSON: {"key": "value"} and $another_var'
        )

    def test_preserve_defaults_with_converted_variables(self):
        """Test that defaults are preserved when variables are converted"""
        latitude_data = {
            "content": "Hello {{name}}, your score is {{score}}",
            "parameters": {"name": "User", "score": 100},
        }

        result = extract_template_data(latitude_data)
        assert result["prompt"] == "Hello $name, your score is $score"
        assert result["defaults"] == {"name": "User", "score": 100}
