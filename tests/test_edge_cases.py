"""Edge case tests for llm-templates-latitude"""

from unittest.mock import Mock, patch

import pytest

from lat import LatitudeClient
from tests.fixtures import (
    SAMPLE_UUIDS,
    create_prompt_with_frontmatter,
)
from utils import extract_template_data, is_uuid_like, parse_template_path


class TestPathParsingEdgeCases:
    """Test edge cases for template path parsing"""

    def test_parse_template_path_with_slashes_in_document_name(self):
        """Test document paths containing slashes"""
        project_id, version_uuid, doc_path = parse_template_path(
            f"12345/{SAMPLE_UUIDS[0]}/folder/subfolder/document"
        )
        assert project_id == "12345"
        assert version_uuid == SAMPLE_UUIDS[0]
        assert doc_path == "folder/subfolder/document"

    def test_parse_template_path_with_special_characters(self):
        """Test paths with special characters"""
        project_id, version_uuid, doc_path = parse_template_path(
            f"12345/{SAMPLE_UUIDS[0]}/email-template_v2.1"
        )
        assert project_id == "12345"
        assert doc_path == "email-template_v2.1"

    def test_parse_template_path_very_long_path(self):
        """Test with very long paths"""
        long_path = "/".join([f"segment{i}" for i in range(20)])
        project_id, version_uuid, doc_path = parse_template_path(
            f"12345/{SAMPLE_UUIDS[0]}/{long_path}"
        )
        assert project_id == "12345"
        assert doc_path == long_path

    def test_is_uuid_like_edge_cases(self):
        """Test UUID detection edge cases"""
        # Valid UUIDs with different cases
        assert is_uuid_like("550E8400-E29B-41D4-A716-446655440000") is True
        assert is_uuid_like("550e8400-e29b-41d4-a716-446655440000") is True

        # Invalid patterns that look similar
        assert (
            is_uuid_like("550e8400-e29b-41d4-a716-44665544000g") is False
        )  # 'g' is invalid
        assert is_uuid_like("550e8400-e29b-41d4-a716") is False  # Too short
        assert is_uuid_like("550e8400e29b41d4a716446655440000") is False  # No dashes
        assert (
            is_uuid_like("550e8400-e29b-41d4-a716-446655440000-") is False
        )  # Extra dash
        assert (
            is_uuid_like("g50e8400-e29b-41d4-a716-446655440000") is False
        )  # Invalid char

        # "live" is not a UUID but should be handled separately
        assert is_uuid_like("live") is False
        assert is_uuid_like("LIVE") is False
        assert is_uuid_like("Live") is False


class TestLiveVersionParsing:
    """Test parsing paths with 'live' version indicator"""

    def test_parse_live_version_with_document(self):
        """Test parsing project/live/document format"""
        project_id, version_uuid, doc_path = parse_template_path("12345/live/my-prompt")
        assert project_id == "12345"
        assert version_uuid == "live"
        assert doc_path == "my-prompt"

    def test_parse_live_version_nested_path(self):
        """Test parsing with nested document paths and live"""
        project_id, version_uuid, doc_path = parse_template_path(
            "99999/live/folder/subfolder/doc"
        )
        assert project_id == "99999"
        assert version_uuid == "live"
        assert doc_path == "folder/subfolder/doc"

    def test_parse_live_case_sensitivity(self):
        """Test that 'live' is case sensitive"""
        # Should work with lowercase 'live'
        project_id, version_uuid, doc_path = parse_template_path("12345/live/doc")
        assert version_uuid == "live"

        # Should NOT work with other cases (they're not valid UUIDs either)
        import pytest

        with pytest.raises(ValueError):
            parse_template_path("12345/LIVE/doc")

        with pytest.raises(ValueError):
            parse_template_path("12345/Live/doc")


class TestFrontmatterEdgeCases:
    """Test edge cases for YAML frontmatter parsing"""

    def test_multiple_yaml_blocks(self):
        """Test content with multiple YAML-like blocks"""
        content = """---
provider: openai
---

Some content here

---
This looks like YAML but it's not
---

More content"""

        data = {"content": content}
        result = extract_template_data(data)

        # Should only remove the first frontmatter
        assert "Some content here" in result["prompt"]
        assert "This looks like YAML" in result["prompt"]

    def test_frontmatter_with_unicode(self):
        """Test frontmatter with Unicode characters"""
        content = create_prompt_with_frontmatter(
            "Genera una historia en español sobre niños",
            metadata={"author": "José García", "title": "Café con leche"},
        )

        data = {"content": content}
        result = extract_template_data(data)

        assert result["prompt"] == "Genera una historia en español sobre niños"

    def test_empty_frontmatter_variations(self):
        """Test various empty frontmatter patterns"""
        test_cases = [
            ("---\n---\nContent", "Content"),
            ("---\n\n---\nContent", "Content"),
            ("---\n \n---\nContent", "Content"),
            ("---\n\t\n---\nContent", "Content"),
        ]

        for content, expected in test_cases:
            data = {"content": content}
            result = extract_template_data(data)
            assert result["prompt"] == expected

    def test_frontmatter_only_no_content(self):
        """Test frontmatter without actual content"""
        content = """---
provider: openai
model: gpt-4
---"""

        data = {"content": content}
        result = extract_template_data(data)

        # Should keep original if no content after frontmatter
        assert "---" in result["prompt"]

    def test_nested_yaml_in_frontmatter(self):
        """Test deeply nested YAML structures"""
        content = """---
provider: openai
config:
  model:
    name: gpt-4
    version: latest
  parameters:
    temperature: 0.8
    penalties:
      frequency: 0.5
      presence: 0.5
metadata:
  tags: [ai, chatbot, assistant]
  versions:
    - 1.0
    - 1.1
---

Actual prompt content"""

        data = {"content": content}
        result = extract_template_data(data)
        assert result["prompt"] == "Actual prompt content"


class TestLargeDataHandling:
    """Test handling of large data"""

    def test_very_large_prompt(self):
        """Test with very large prompt content"""
        # Create a 1MB prompt
        large_content = "x" * (1024 * 1024)
        data = {"content": large_content}

        result = extract_template_data(data)
        assert len(result["prompt"]) == 1024 * 1024

    def test_many_parameters(self):
        """Test with many parameters"""
        parameters = {f"param_{i}": f"value_{i}" for i in range(1000)}
        data = {"content": "Test prompt", "parameters": parameters}

        result = extract_template_data(data)
        assert len(result["defaults"]) == 1000

    def test_deeply_nested_options(self):
        """Test with deeply nested configuration"""

        def create_nested_dict(depth):
            if depth == 0:
                return {"value": "test"}
            return {"nested": create_nested_dict(depth - 1)}

        data = {"content": "Test prompt", "model_config": create_nested_dict(10)}

        result = extract_template_data(data)
        assert "options" in result

        # Verify deep nesting is preserved
        current = result["options"]
        for _ in range(10):
            assert "nested" in current
            current = current["nested"]
        assert current == {"value": "test"}


class TestErrorRecovery:
    """Test error recovery and resilience"""

    def test_partial_response_handling(self):
        """Test handling of partial/incomplete responses"""
        # Valid cases that should work
        valid_cases = [
            ({"content": ""}, ""),  # Empty content
            ({"content": " \n\t "}, " \n\t "),  # Whitespace only
            ({"content": "Valid content"}, "Valid content"),  # Normal content
        ]

        for data, expected_prompt in valid_cases:
            result = extract_template_data(data)
            assert result.get("prompt") == expected_prompt

        # Invalid cases that should result in empty or missing prompt
        invalid_cases = [
            {"content": None},  # None content
            {},  # Missing content field
            {"prompt": None},  # None prompt field
        ]

        for data in invalid_cases:
            result = extract_template_data(data)
            # Should either not have prompt field or have None/empty value
            assert (
                "prompt" not in result
                or result.get("prompt") is None
                or result.get("prompt") == ""
            )

    def test_malformed_data_structures(self):
        """Test with malformed data structures"""
        test_cases = [
            # String instead of dict for parameters
            {"content": "Test", "parameters": "not a dict"},
            # List instead of dict for model_config
            {"content": "Test", "model_config": ["not", "a", "dict"]},
            # Null values
            {"content": "Test", "parameters": None, "model_config": None},
        ]

        for data in test_cases:
            # Should not raise an exception
            result = extract_template_data(data)
            assert "prompt" in result
            # Invalid fields should be ignored
            if not isinstance(data.get("parameters"), dict):
                assert "defaults" not in result
            if not isinstance(data.get("model_config"), dict):
                assert "options" not in result


class TestHTTPClientEdgeCases:
    """Test edge cases specific to HTTP client"""

    @patch("lat.httpx.Client")
    def test_timeout_handling(self, mock_client_class):
        """Test handling of request timeouts"""
        import httpx

        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

        client = LatitudeClient("test-key")

        with pytest.raises(Exception) as exc_info:
            client.get_document("12345", "uuid", "doc")

        assert (
            "Failed to connect" in str(exc_info.value)
            or "timeout" in str(exc_info.value).lower()
        )

    @patch("lat.httpx.Client")
    def test_invalid_json_response(self, mock_client_class):
        """Test handling of invalid JSON responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Not valid JSON"

        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        client = LatitudeClient("test-key")

        with pytest.raises(Exception) as exc_info:
            client.get_document("12345", "uuid", "doc")

        assert "Error loading document" in str(exc_info.value)


class TestConcurrentAccess:
    """Test concurrent access scenarios"""

    def test_multiple_parse_calls(self):
        """Test multiple simultaneous parse calls"""
        # This is mainly to ensure thread safety of parsing functions
        paths = [
            f"{12000 + i}/{SAMPLE_UUIDS[i % len(SAMPLE_UUIDS)]}/doc-{i}"
            for i in range(100)
        ]

        results = []
        for path in paths:
            project_id, version_uuid, doc_path = parse_template_path(path)
            results.append((project_id, version_uuid, doc_path))

        # Verify all parses succeeded
        assert len(results) == 100
        for i, (project_id, version_uuid, doc_path) in enumerate(results):
            assert project_id == str(12000 + i)
            assert doc_path == f"doc-{i}"
