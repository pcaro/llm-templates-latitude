"""Tests for lat_sdk module - SDK implementation of Latitude client"""

# Skip all tests in this module if latitude_sdk is not available
import importlib.util
from unittest.mock import Mock, patch

import pytest

SDK_AVAILABLE = importlib.util.find_spec("latitude_sdk") is not None

# Skip the entire module if SDK is not available
pytestmark = pytest.mark.skipif(not SDK_AVAILABLE, reason="latitude-sdk not installed")

# Import lat_sdk only if we're going to run the tests
if SDK_AVAILABLE:
    from lat_sdk import LatitudeClient
    from utils import (
        LatitudeAPIError,
        LatitudeAuthenticationError,
        LatitudeNotFoundError,
        extract_template_data,
        is_uuid_like,
        parse_template_path,
    )


class TestLatitudeSDKClient:
    """Test SDK client implementation"""

    def test_client_initialization_without_project(self):
        """Test client initialization without project ID"""
        with patch("lat_sdk.Latitude") as mock_latitude:
            client = LatitudeClient("test-api-key")

            assert client.api_key == "test-api-key"
            assert client.current_project_id is None
            mock_latitude.assert_called_once_with("test-api-key")

    def test_client_initialization_with_project(self):
        """Test client initialization with project ID"""
        with patch("lat_sdk.Latitude") as mock_latitude:
            with patch("lat_sdk.LatitudeOptions") as mock_options:
                client = LatitudeClient("test-api-key", "12345")

                assert client.api_key == "test-api-key"
                assert client.current_project_id == "12345"
                mock_options.assert_called_once_with(project_id=12345)
                mock_latitude.assert_called_once()

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_get_document_success(self, mock_latitude_class, mock_asyncio_run):
        """Test successful document retrieval"""
        # Setup mock SDK response
        mock_sdk_response = {
            "content": "Test prompt content",
            "system": "You are helpful",
            "parameters": {"name": "User"},
            "config": {"temperature": 0.8},
        }
        mock_asyncio_run.return_value = mock_sdk_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        # Verify normalized response
        assert result["prompt"] == "Test prompt content"
        assert result["system"] == "You are helpful"
        assert result["defaults"] == {"name": "User"}
        assert result["options"] == {"temperature": 0.8}

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_get_document_with_frontmatter(self, mock_latitude_class, mock_asyncio_run):
        """Test document with YAML frontmatter is parsed correctly"""
        # Setup mock SDK response with frontmatter
        mock_sdk_response = {
            "content": "---\nprovider: openai\nmodel: gpt-4\n---\n\nActual prompt content here",
            "parameters": {},
        }
        mock_asyncio_run.return_value = mock_sdk_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        # Verify frontmatter is removed
        assert result["prompt"] == "Actual prompt content here"
        assert "provider" not in str(result)
        assert "model" not in str(result)

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_get_document_filters_problematic_fields(
        self, mock_latitude_class, mock_asyncio_run
    ):
        """Test that problematic fields are filtered from options"""
        # Setup mock SDK response with problematic fields
        mock_sdk_response = {
            "content": "Test prompt",
            "config": {
                "model": "gpt-4",  # Should be filtered
                "provider": "openai",  # Should be filtered
                "temperature": 0.8,  # Should be kept
                "max_tokens": 1000,  # Should be kept
            },
        }
        mock_asyncio_run.return_value = mock_sdk_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        # Verify problematic fields are filtered
        assert "options" in result
        assert "temperature" in result["options"]
        assert "max_tokens" in result["options"]
        assert "model" not in result["options"]
        assert "provider" not in result["options"]

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_get_document_authentication_error(
        self, mock_latitude_class, mock_asyncio_run
    ):
        """Test authentication error handling"""
        mock_asyncio_run.side_effect = Exception("Unauthorized access")

        client = LatitudeClient("test-api-key")

        with pytest.raises(LatitudeAuthenticationError) as exc_info:
            client.get_document(
                "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
            )

        assert "Invalid Latitude API key" in str(exc_info.value)

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_get_document_not_found_error(self, mock_latitude_class, mock_asyncio_run):
        """Test not found error handling"""
        mock_asyncio_run.side_effect = Exception("404 Not Found")

        client = LatitudeClient("test-api-key")

        with pytest.raises(LatitudeNotFoundError) as exc_info:
            client.get_document(
                "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
            )

        assert "Document not found" in str(exc_info.value)

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_get_document_network_error(self, mock_latitude_class, mock_asyncio_run):
        """Test network error handling"""
        mock_asyncio_run.side_effect = Exception("No address associated with hostname")

        client = LatitudeClient("test-api-key")

        with pytest.raises(LatitudeAPIError) as exc_info:
            client.get_document(
                "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
            )

        assert "Failed to connect to Latitude API" in str(exc_info.value)

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    @patch("lat_sdk.LatitudeOptions")
    def test_project_context_switching(
        self, mock_options, mock_latitude_class, mock_asyncio_run
    ):
        """Test that SDK reinitializes when project ID changes"""
        mock_asyncio_run.return_value = {"content": "Test"}

        client = LatitudeClient("test-api-key", "12345")
        assert client.current_project_id == "12345"

        # First call with same project - should reinitialize with version context
        client.get_document("12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc")
        assert (
            mock_latitude_class.call_count == 2
        )  # 1 in constructor + 1 for version context

        # Second call with different project
        client.get_document(
            "67890", "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "test-doc2"
        )
        assert client.current_project_id == "67890"
        assert (
            mock_latitude_class.call_count == 3
        )  # 1 constructor + 1 first call + 1 project change
        # Verify the latest call includes both project_id and version_uuid
        mock_options.assert_called_with(
            project_id=67890, version_uuid="6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        )

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    @patch("lat_sdk.LatitudeOptions")
    def test_version_context_switching(
        self, mock_options, mock_latitude_class, mock_asyncio_run
    ):
        """Test that SDK reinitializes when version UUID changes"""
        mock_asyncio_run.return_value = {"content": "Test"}

        client = LatitudeClient("test-api-key", "12345")

        # First call with version A
        client.get_document("12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc")
        assert client.current_version_uuid == "550e8400-e29b-41d4-a716-446655440000"
        initial_call_count = mock_latitude_class.call_count

        # Second call with same project but different version
        client.get_document("12345", "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "test-doc")
        assert client.current_version_uuid == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert mock_latitude_class.call_count == initial_call_count + 1
        # Verify the latest call includes the new version
        mock_options.assert_called_with(
            project_id=12345, version_uuid="6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        )

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    @patch("lat_sdk.LatitudeOptions")
    def test_no_reinit_when_context_same(
        self, mock_options, mock_latitude_class, mock_asyncio_run
    ):
        """Test that SDK doesn't reinitialize when project and version are the same"""
        mock_asyncio_run.return_value = {"content": "Test"}

        client = LatitudeClient("test-api-key", "12345")

        # First call
        client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc1"
        )
        initial_call_count = mock_latitude_class.call_count

        # Second call with same project and version
        client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc2"
        )

        # Should not have reinitialized
        assert mock_latitude_class.call_count == initial_call_count

    def test_normalize_sdk_response_with_object(self):
        """Test normalization when SDK returns an object"""
        mock_response = Mock()
        mock_response.content = "Test prompt"
        mock_response.system = "System prompt"
        mock_response.parameters = {"key": "value"}

        client = LatitudeClient("test-api-key")
        normalized = client._normalize_sdk_response(mock_response)

        assert normalized["prompt"] == "Test prompt"
        assert normalized["system"] == "System prompt"
        assert normalized["defaults"] == {"key": "value"}

    def test_normalize_sdk_response_missing_content(self):
        """Test error when content is missing"""
        mock_response = {"system": "System prompt"}

        client = LatitudeClient("test-api-key")

        with pytest.raises(LatitudeAPIError) as exc_info:
            client._normalize_sdk_response(mock_response)

        assert "No prompt content found" in str(exc_info.value)

    def test_normalize_sdk_response_empty_optionals(self):
        """Test that empty optional fields are excluded"""
        mock_response = {
            "content": "Test prompt",
            "system": "",  # Empty string - should be excluded
            "parameters": {},  # Empty dict - should be excluded
            "config": {"temperature": 0.8},  # Non-empty - should be included
        }

        client = LatitudeClient("test-api-key")
        normalized = client._normalize_sdk_response(mock_response)

        assert normalized["prompt"] == "Test prompt"
        assert "system" not in normalized
        assert "defaults" not in normalized
        assert "options" in normalized
        assert normalized["options"] == {"temperature": 0.8}


class TestSDKHelperFunctions:
    """Test helper functions that SDK implementation imports from lat.py"""

    def test_parse_template_path(self):
        """Test that parse_template_path is imported correctly"""
        # Should use the same implementation as lat.py
        project_id, version_uuid, doc_path = parse_template_path(
            "12345/550e8400-e29b-41d4-a716-446655440000/doc-name"
        )
        assert project_id == "12345"
        assert version_uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert doc_path == "doc-name"

    def test_is_uuid_like(self):
        """Test that is_uuid_like is imported correctly"""
        # Should use the same implementation as lat.py
        assert is_uuid_like("550e8400-e29b-41d4-a716-446655440000") is True
        assert is_uuid_like("not-a-uuid") is False

    def test_extract_template_data(self):
        """Test that extract_template_data is imported correctly"""
        # Should use the same implementation as lat.py
        data = {"content": "Test", "system": "System"}
        result = extract_template_data(data)
        assert result["prompt"] == "Test"
        assert result["system"] == "System"

    def test_get_client_implementation(self):
        """Test that client implementation returns 'sdk'"""
        from lat_sdk import get_client_implementation

        assert get_client_implementation() == "sdk"


class TestSDKEdgeCases:
    """Test edge cases specific to SDK implementation"""

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_complex_yaml_frontmatter(self, mock_latitude_class, mock_asyncio_run):
        """Test complex YAML frontmatter with nested structures"""
        mock_response = {
            "content": """---
provider: openai
model: gpt-4
config:
  temperature: 0.8
  max_tokens: 1000
metadata:
  author: test
  version: 1.0
---

This is the actual prompt content
with multiple lines""",
            "parameters": {},
        }
        mock_asyncio_run.return_value = mock_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        # Verify only prompt content is extracted
        assert (
            result["prompt"] == "This is the actual prompt content\nwith multiple lines"
        )
        assert "provider" not in str(result)
        assert "metadata" not in str(result)

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_malformed_frontmatter(self, mock_latitude_class, mock_asyncio_run):
        """Test malformed frontmatter (missing closing ---)"""
        mock_response = {
            "content": """---
provider: openai
This is not valid YAML and has no closing ---
But it should still work as content""",
            "parameters": {},
        }
        mock_asyncio_run.return_value = mock_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        # Should keep original content since frontmatter is malformed
        assert "---" in result["prompt"]
        assert "provider: openai" in result["prompt"]

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_empty_frontmatter(self, mock_latitude_class, mock_asyncio_run):
        """Test empty frontmatter"""
        mock_response = {
            "content": """---
---
Actual content here""",
            "parameters": {},
        }
        mock_asyncio_run.return_value = mock_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        assert result["prompt"] == "Actual content here"

    @patch("lat_sdk.asyncio.run")
    @patch("lat_sdk.Latitude")
    def test_unicode_in_prompt(self, mock_latitude_class, mock_asyncio_run):
        """Test Unicode characters in prompt content"""
        mock_response = {
            "content": "Test with émojis 🎉 and ñiños café",
            "system": "Système avec français",
            "parameters": {"name": "José García"},
        }
        mock_asyncio_run.return_value = mock_response

        client = LatitudeClient("test-api-key")
        result = client.get_document(
            "12345", "550e8400-e29b-41d4-a716-446655440000", "test-doc"
        )

        assert "émojis 🎉" in result["prompt"]
        assert "français" in result["system"]
        assert result["defaults"]["name"] == "José García"
