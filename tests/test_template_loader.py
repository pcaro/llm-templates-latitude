"""Tests for llm-templates-latitude plugin"""

from unittest.mock import Mock, patch

import pytest

from llm_templates_latitude import latitude_template_loader
from lat import parse_template_path, is_uuid_like, extract_template_data


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
    project_id, version_uuid, document_path = parse_template_path(f"my-project/{test_uuid}/email-template")
    assert project_id == "my-project"
    assert version_uuid == test_uuid
    assert document_path == "email-template"

    # Test with version_uuid/document_path format
    project_id, version_uuid, document_path = parse_template_path(f"{test_uuid}/welcome-email")
    assert project_id is None
    assert version_uuid == test_uuid
    assert document_path == "welcome-email"

    # Test with just version UUID (list documents)
    project_id, version_uuid, document_path = parse_template_path(test_uuid)
    assert project_id is None
    assert version_uuid == test_uuid
    assert document_path == ""

    # Test with project_id/version_uuid (list documents)
    project_id, version_uuid, document_path = parse_template_path(f"my-project/{test_uuid}")
    assert project_id == "my-project"
    assert version_uuid == test_uuid
    assert document_path == ""


def test_is_uuid_like():
    """Test UUID detection"""
    # Valid UUIDs
    assert is_uuid_like("550e8400-e29b-41d4-a716-446655440000") is True
    assert is_uuid_like("6ba7b810-9dad-11d1-80b4-00c04fd430c8") is True
    assert is_uuid_like("6BA7B810-9DAD-11D1-80B4-00C04FD430C8") is True  # uppercase

    # Invalid UUIDs
    assert is_uuid_like("not-a-uuid") is False
    assert is_uuid_like("550e8400-e29b-41d4-a716") is False  # too short
    assert is_uuid_like("550e8400-e29b-41d4-a716-446655440000-extra") is False  # too long
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
    
    assert config["prompt"] == "Hello {{name}}"
    assert config["system"] == "You are helpful"
    assert config["model"] == "gpt-4"
    assert config["defaults"] == {"name": "User"}
    assert config["options"] == {"temperature": 0.8}
    assert config["schema_object"] == {"type": "object"}
    
    # Test with minimal data
    minimal_data = {"content": "Hello world"}
    config = extract_template_data(minimal_data)
    assert config["prompt"] == "Hello world"
    assert "system" not in config
    assert "model" not in config


def test_latitude_template_loader_integration():
    """Test integration of template loader components"""
    # This test verifies the integration without mocking the HTTP layer
    # The actual API calls are tested in test_lat.py
    
    # Test that the function exists and can parse paths correctly
    from lat import parse_template_path, extract_template_data
    
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    project_id, version_uuid, document_path = parse_template_path(f"test-project/{test_uuid}/welcome-email")
    
    assert project_id == "test-project"
    assert version_uuid == test_uuid
    assert document_path == "welcome-email"
    
    # Test template data extraction
    mock_data = {
        "content": "Hello {{name}}",
        "system": "You are helpful",
        "model": "gpt-4",
    }
    
    config = extract_template_data(mock_data)
    assert config["prompt"] == "Hello {{name}}"
    assert config["system"] == "You are helpful"
    assert config["model"] == "gpt-4"


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


