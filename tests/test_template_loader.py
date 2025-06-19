"""Tests for llm-templates-latitude plugin"""

from unittest.mock import Mock, patch

import pytest

from llm_templates_latitude import _parse_template_path, latitude_template_loader, _is_uuid_like


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
    # Test with project_id/prompt_path format
    project_id, prompt_path, is_uuid = _parse_template_path("my-project/email-template")
    assert project_id == "my-project"
    assert prompt_path == "email-template"
    assert is_uuid is False

    # Test with nested prompt path
    project_id, prompt_path, is_uuid = _parse_template_path("proj123/marketing/emails/welcome")
    assert project_id == "proj123"
    assert prompt_path == "marketing/emails/welcome"
    assert is_uuid is False

    # Test with just prompt path (no project)
    project_id, prompt_path, is_uuid = _parse_template_path("simple-prompt")
    assert project_id is None
    assert prompt_path == "simple-prompt"
    assert is_uuid is False

    # Test with UUID
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    project_id, uuid_str, is_uuid = _parse_template_path(test_uuid)
    assert project_id is None
    assert uuid_str == test_uuid
    assert is_uuid is True

    # Test with project_id/UUID format
    project_id, uuid_str, is_uuid = _parse_template_path(f"my-project/{test_uuid}")
    assert project_id == "my-project"
    assert uuid_str == test_uuid
    assert is_uuid is True


def test_is_uuid_like():
    """Test UUID detection"""
    # Valid UUIDs
    assert _is_uuid_like("550e8400-e29b-41d4-a716-446655440000") is True
    assert _is_uuid_like("6ba7b810-9dad-11d1-80b4-00c04fd430c8") is True
    assert _is_uuid_like("6BA7B810-9DAD-11D1-80B4-00C04FD430C8") is True  # uppercase

    # Invalid UUIDs
    assert _is_uuid_like("not-a-uuid") is False
    assert _is_uuid_like("550e8400-e29b-41d4-a716") is False  # too short
    assert _is_uuid_like("550e8400-e29b-41d4-a716-446655440000-extra") is False  # too long
    assert _is_uuid_like("marketing/email-template") is False


@patch("llm_templates_latitude.httpx.Client")
@patch("llm_templates_latitude._get_api_key")
def test_latitude_template_loader_success(mock_get_api_key, mock_httpx_client):
    """Test successful template loading from Latitude"""
    # Setup mocks
    mock_get_api_key.return_value = "test-api-key"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Hello {{name}}, welcome to our service!",
        "system": "You are a helpful assistant",
        "model": "gpt-4",
        "parameters": {"name": "User"},
        "model_config": {"temperature": 0.7},
    }
    mock_response.raise_for_status.return_value = None

    mock_client = Mock()
    mock_client.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__ = Mock(return_value=mock_client)
    mock_httpx_client.return_value.__exit__ = Mock(return_value=None)

    # Test the loader
    template = latitude_template_loader("test-project/welcome-email")

    # Verify the template was created correctly
    assert template.name == "test-project/welcome-email"
    assert template.prompt == "Hello {{name}}, welcome to our service!"
    assert template.system == "You are a helpful assistant"
    assert template.model == "gpt-4"
    assert template.defaults == {"name": "User"}
    assert template.options == {"temperature": 0.7}

    # Verify API was called correctly
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert "test-project" in call_args[0][0]  # URL contains project ID
    assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"


@patch("llm_templates_latitude.httpx.Client")
@patch("llm_templates_latitude._get_api_key")
def test_latitude_template_loader_404(mock_get_api_key, mock_httpx_client):
    """Test handling of 404 errors from Latitude API"""
    from httpx import HTTPStatusError, Request, Response

    mock_get_api_key.return_value = "test-api-key"

    # Create a proper HTTPStatusError
    request = Request(
        "GET", "https://gateway.latitude.so/api/v1/prompts/nonexistent-prompt"
    )
    response = Response(404, request=request)
    http_error = HTTPStatusError("404 Not Found", request=request, response=response)

    mock_client = Mock()
    mock_client.get.side_effect = http_error
    mock_httpx_client.return_value.__enter__ = Mock(return_value=mock_client)
    mock_httpx_client.return_value.__exit__ = Mock(return_value=None)

    # Test that 404 raises appropriate error
    with pytest.raises(ValueError, match="Prompt not found"):
        latitude_template_loader("nonexistent-prompt")


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


def test_create_llm_template_minimal():
    """Test creating LLM template with minimal data"""
    from llm_templates_latitude import _create_llm_template

    data = {"content": "Hello world"}
    template = _create_llm_template("test-template", data)

    assert template.name == "test-template"
    assert template.prompt == "Hello world"
    assert template.system is None
    assert template.model is None


def test_create_llm_template_full():
    """Test creating LLM template with all available data"""
    from llm_templates_latitude import _create_llm_template

    data = {
        "content": "Hello {{name}}",
        "system": "You are helpful",
        "model": "gpt-4",
        "parameters": {"name": "User"},
        "model_config": {"temperature": 0.8},
        "schema": {"type": "object"},
    }

    template = _create_llm_template("full-template", data)

    assert template.name == "full-template"
    assert template.prompt == "Hello {{name}}"
    assert template.system == "You are helpful"
    assert template.model == "gpt-4"
    assert template.defaults == {"name": "User"}
    assert template.options == {"temperature": 0.8}
    assert template.schema_object == {"type": "object"}
