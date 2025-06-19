"""Tests for lat.py module"""

from unittest.mock import Mock, patch
import pytest
from lat import (
    LatitudeClient,
    LatitudeAPIError,
    LatitudeAuthenticationError,
    LatitudeNotFoundError,
    parse_template_path,
    is_uuid_like,
    extract_template_data,
)


@patch("lat.httpx.Client")
def test_latitude_client_get_document_success(mock_httpx_client):
    """Test successful document retrieval"""
    # Setup mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "Test prompt content",
        "system": "Test system prompt"
    }
    mock_response.raise_for_status.return_value = None
    
    mock_client = Mock()
    mock_client.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__ = Mock(return_value=mock_client)
    mock_httpx_client.return_value.__exit__ = Mock(return_value=None)
    
    # Test
    client = LatitudeClient("test-api-key")
    result = client.get_document("project123", "550e8400-e29b-41d4-a716-446655440000", "test-doc")
    
    # Verify
    assert result["content"] == "Test prompt content"
    assert result["system"] == "Test system prompt"
    
    # Verify API call
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert "project123" in call_args[0][0]
    assert "550e8400-e29b-41d4-a716-446655440000" in call_args[0][0]
    assert "test-doc" in call_args[0][0]
    assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"


@patch("lat.httpx.Client")
def test_latitude_client_authentication_error(mock_httpx_client):
    """Test authentication error handling"""
    # Setup mock for 401 error
    mock_response = Mock()
    mock_response.status_code = 401
    
    mock_client = Mock()
    mock_client.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__ = Mock(return_value=mock_client)
    mock_httpx_client.return_value.__exit__ = Mock(return_value=None)
    
    # Test
    client = LatitudeClient("invalid-key")
    
    with pytest.raises(LatitudeAuthenticationError, match="Invalid Latitude API key"):
        client.get_document("project123", "550e8400-e29b-41d4-a716-446655440000", "test-doc")


@patch("lat.httpx.Client")
def test_latitude_client_not_found_error(mock_httpx_client):
    """Test not found error handling"""
    # Setup mock for 404 error
    mock_response = Mock()
    mock_response.status_code = 404
    
    mock_client = Mock()
    mock_client.get.return_value = mock_response
    mock_httpx_client.return_value.__enter__ = Mock(return_value=mock_client)
    mock_httpx_client.return_value.__exit__ = Mock(return_value=None)
    
    # Test
    client = LatitudeClient("test-api-key")
    
    with pytest.raises(LatitudeNotFoundError, match="Document not found: nonexistent"):
        client.get_document("project123", "550e8400-e29b-41d4-a716-446655440000", "nonexistent")


def test_parse_template_path_valid_formats():
    """Test parsing various valid template path formats"""
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    
    # Full format
    project_id, version_uuid, document_path = parse_template_path(f"proj/{test_uuid}/doc")
    assert project_id == "proj"
    assert version_uuid == test_uuid
    assert document_path == "doc"
    
    # Version + document
    project_id, version_uuid, document_path = parse_template_path(f"{test_uuid}/doc")
    assert project_id is None
    assert version_uuid == test_uuid
    assert document_path == "doc"
    
    # Just version
    project_id, version_uuid, document_path = parse_template_path(test_uuid)
    assert project_id is None
    assert version_uuid == test_uuid
    assert document_path == ""


def test_parse_template_path_invalid_formats():
    """Test parsing invalid template path formats"""
    
    # Invalid single part (not UUID)
    with pytest.raises(ValueError, match="Invalid format"):
        parse_template_path("not-a-uuid")
    
    # Invalid second part (not UUID)
    with pytest.raises(ValueError, match="Second part must be a version UUID"):
        parse_template_path("project/not-a-uuid")
    
    # Invalid version UUID in full format
    with pytest.raises(ValueError, match="Invalid version UUID"):
        parse_template_path("project/not-a-uuid/document")


def test_is_uuid_like():
    """Test UUID validation"""
    # Valid UUIDs
    assert is_uuid_like("550e8400-e29b-41d4-a716-446655440000")
    assert is_uuid_like("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    assert is_uuid_like("6BA7B810-9DAD-11D1-80B4-00C04FD430C8")  # uppercase
    
    # Invalid formats
    assert not is_uuid_like("not-a-uuid")
    assert not is_uuid_like("550e8400-e29b-41d4-a716")  # too short
    assert not is_uuid_like("550e8400-e29b-41d4-a716-446655440000-extra")  # too long
    assert not is_uuid_like("project/document")


def test_extract_template_data():
    """Test template data extraction"""
    # Full data
    data = {
        "content": "Hello {{name}}",
        "system": "You are helpful",
        "model": "gpt-4",
        "parameters": {"name": "User"},
        "model_config": {"temperature": 0.8},
        "schema": {"type": "object"},
    }
    
    config = extract_template_data(data)
    
    assert config["prompt"] == "Hello $name"  # Variables converted from {{}} to $
    assert config["system"] == "You are helpful"
    assert "model" not in config  # Model is now filtered out
    assert config["defaults"] == {"name": "User"}
    assert config["options"] == {"temperature": 0.8}
    assert config["schema_object"] == {"type": "object"}
    
    # Alternative field names
    alt_data = {
        "prompt": "Alt prompt",
        "system_prompt": "Alt system",
        "recommended_model": "claude-3",
        "defaults": {"param": "value"},
        "options": {"max_tokens": 100},
        "json_schema": {"type": "string"},
    }
    
    config = extract_template_data(alt_data)
    
    assert config["prompt"] == "Alt prompt"
    assert config["system"] == "Alt system"
    assert "model" not in config  # Model is filtered even with alternative field names
    assert config["defaults"] == {"param": "value"}
    assert config["options"] == {"max_tokens": 100}
    assert config["schema_object"] == {"type": "string"}
    
    # Minimal data
    minimal = {"content": "Just content"}
    config = extract_template_data(minimal)
    
    assert config["prompt"] == "Just content"
    assert "system" not in config
    assert "model" not in config