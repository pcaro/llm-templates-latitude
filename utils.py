"""
Common utilities for Latitude API clients
"""

import re
from typing import Any, Dict, Optional, Tuple

# Constants
PROBLEMATIC_FIELDS = ["model", "provider", "modelName", "recommended_model"]


class LatitudeAPIError(Exception):
    """Base exception for Latitude API errors"""

    pass


class LatitudeAuthenticationError(LatitudeAPIError):
    """Raised when API key is invalid"""

    pass


class LatitudeNotFoundError(LatitudeAPIError):
    """Raised when document/version is not found"""

    pass


def is_uuid_like(value: str) -> bool:
    """
    Check if a string looks like a UUID

    Args:
        value: String to check

    Returns:
        bool: True if string matches UUID pattern
    """
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, value.lower()))


def parse_template_path(template_path: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Parse template path into project_id, version_uuid, and document_path

    Args:
        template_path: Must be one of:
            - 'project_id/version_uuid/document_path' - Full specification (recommended)
            - 'version_uuid/document_path' - No project ID (tries without project context)

    Returns:
        tuple: (project_id, version_uuid, document_path)

    Raises:
        ValueError: If path format is invalid
    """
    parts = template_path.split("/")

    if len(parts) >= 3:
        # project_id/version_uuid/document_path (with possible nested paths)
        project_id, version_uuid = parts[0], parts[1]
        document_path = "/".join(parts[2:])  # Join remaining parts for nested paths

        # Validate second part is UUID or "live"
        if version_uuid != "live" and not is_uuid_like(version_uuid):
            raise ValueError(f"Invalid version UUID: {version_uuid}")

        return project_id, version_uuid, document_path

    elif len(parts) == 2:
        # version_uuid/document_path (no project_id)
        version_uuid, document_path = parts

        # Validate first part is UUID or "live"
        if version_uuid != "live" and not is_uuid_like(version_uuid):
            raise ValueError("Second part must be a version UUID or 'live'")

        return None, version_uuid, document_path

    elif len(parts) == 1:
        # Single part must be a UUID (not supported for documents)
        single_part = parts[0]
        if not is_uuid_like(single_part):
            raise ValueError(f"Invalid format: {template_path}")

        # This would be for listing documents, but that's not implemented
        return None, single_part, ""

    else:
        raise ValueError(f"Invalid template path format: {template_path}")


def convert_latitude_variables(text: str) -> str:
    """
    Convert Latitude's {{variable}} syntax to LLM's $variable syntax

    Args:
        text: Text with {{variable}} patterns

    Returns:
        str: Text with $variable patterns
    """
    return re.sub(r"\{\{(\w+)\}\}", r"$\1", text)


def strip_yaml_frontmatter(content: str) -> str:
    """
    Remove YAML frontmatter from content if present

    Args:
        content: Content that may have YAML frontmatter

    Returns:
        str: Content with frontmatter removed
    """
    if content.startswith("---\n"):
        end_marker = "\n---\n"
        end_pos = content.find(end_marker)
        if end_pos != -1:
            actual_content = content[end_pos + len(end_marker) :].strip()
            if actual_content:
                return actual_content
    return content


def filter_problematic_fields(options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out fields that cause "Extra inputs are not permitted" errors

    Args:
        options: Dictionary of options to filter

    Returns:
        dict: Filtered options without problematic fields
    """
    return {
        key: value for key, value in options.items() if key not in PROBLEMATIC_FIELDS
    }


def extract_template_data(latitude_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract template configuration from Latitude API response

    Args:
        latitude_data: Raw response from Latitude API

    Returns:
        dict: Template configuration for LLM
    """
    if not isinstance(latitude_data, dict):
        raise ValueError("Expected dict from Latitude API")

    # Get content from various possible field names
    content = None
    for content_field in ["content", "prompt"]:
        if content_field in latitude_data:
            content = latitude_data[content_field]
            break

    if content is None:
        return {}

    # Strip YAML frontmatter if present
    prompt_content = strip_yaml_frontmatter(content)

    # Convert variable syntax
    prompt_content = convert_latitude_variables(prompt_content)

    # Start building template config
    template_config = {"prompt": prompt_content}

    # Add system prompt if present and convert variables
    for system_field in ["system", "system_prompt"]:
        if system_field in latitude_data and latitude_data[system_field]:
            template_config["system"] = convert_latitude_variables(
                latitude_data[system_field]
            )
            break

    # Add default parameters if present
    for param_field in ["parameters", "defaults"]:
        if param_field in latitude_data and isinstance(
            latitude_data[param_field], dict
        ):
            template_config["defaults"] = latitude_data[param_field]
            break

    # Process model configuration options
    for option_field in ["model_config", "options"]:
        if option_field in latitude_data and isinstance(
            latitude_data[option_field], dict
        ):
            # Filter out problematic fields
            filtered_options = filter_problematic_fields(latitude_data[option_field])
            if filtered_options:
                template_config["options"] = filtered_options
            break

    # Add JSON schema if present
    for schema_field in ["schema", "json_schema"]:
        if schema_field in latitude_data and latitude_data[schema_field]:
            template_config["schema_object"] = latitude_data[schema_field]
            break

    return template_config
