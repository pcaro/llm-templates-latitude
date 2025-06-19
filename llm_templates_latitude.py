"""
LLM template loader for Latitude - Load prompts from Latitude as LLM templates
"""

import os
from typing import Any, Dict, Optional

import httpx
import llm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@llm.hookimpl
def register_template_loaders(register):
    """Register Latitude template loader with LLM"""
    register("lat", latitude_template_loader)


def latitude_template_loader(template_path: str) -> llm.Template:
    """
    Load a template from Latitude platform

    Args:
        template_path: Can be one of:
            - 'project_id/version_uuid/document_path' - Full path with project, version, and document
            - 'version_uuid/document_path' - Version and document (project determined automatically)
            - 'project_id/version_uuid' - Project and version (lists all documents)

    Returns:
        llm.Template: Template object with prompt content from Latitude

    Raises:
        ValueError: If API key is missing or template cannot be loaded
    """
    # Get API key from environment or LLM keys
    api_key = _get_api_key()

    # Parse template path
    project_id, version_uuid, document_path = _parse_template_path(template_path)

    # Load template from Latitude
    template_data = _fetch_latitude_template(api_key, project_id, version_uuid, document_path)

    # Create LLM template
    return _create_llm_template(template_path, template_data)


def _get_api_key() -> str:
    """Get Latitude API key from environment variables or LLM keys"""
    # Try environment variable first
    api_key = os.getenv("LATITUDE_API_KEY")
    if api_key:
        return api_key

    # Try LLM keys system
    try:
        api_key = llm.get_key("", "latitude", "LATITUDE_API_KEY")
        if api_key:
            return api_key
    except Exception:
        pass

    raise ValueError(
        "Latitude API key not found. Set LATITUDE_API_KEY environment variable "
        "or configure it with: llm keys set latitude"
    )


def _parse_template_path(template_path: str) -> tuple[Optional[str], Optional[str], str]:
    """
    Parse template path into project_id, version_uuid, and document_path

    Args:
        template_path: Must be one of:
            - 'project_id/version_uuid/document_path' - Full specification (recommended)
            - 'version_uuid/document_path' - Will try without project ID
            - 'project_id/version_uuid' - List all documents in version

    Returns:
        tuple: (project_id, version_uuid, document_path)
    """
    parts = template_path.split("/")

    if len(parts) == 1:
        # Just version UUID - list all documents
        if _is_uuid_like(parts[0]):
            return None, parts[0], ""
        else:
            raise ValueError(
                "Invalid format. Use: project_id/version_uuid/document_path"
            )
    elif len(parts) == 2:
        # Could be version_uuid/document_path or project_id/version_uuid
        if _is_uuid_like(parts[0]):
            # version_uuid/document_path
            return None, parts[0], parts[1]
        elif _is_uuid_like(parts[1]):
            # project_id/version_uuid (list documents)
            return parts[0], parts[1], ""
        else:
            raise ValueError(
                "Invalid format. Second part must be a version UUID. "
                "Use: project_id/version_uuid/document_path"
            )
    elif len(parts) >= 3:
        # project_id/version_uuid/document_path
        project_id, version_uuid = parts[0], parts[1]
        document_path = "/".join(parts[2:])
        
        if not _is_uuid_like(version_uuid):
            raise ValueError(
                f"Invalid version UUID: {version_uuid}. "
                "Use: project_id/version_uuid/document_path"
            )
        
        return project_id, version_uuid, document_path
    else:
        raise ValueError("Invalid template path format")


def _is_uuid_like(value: str) -> bool:
    """
    Check if a string looks like a UUID

    Args:
        value: String to check

    Returns:
        bool: True if it looks like a UUID
    """
    # Basic UUID pattern: 8-4-4-4-12 characters
    import re

    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, value.lower()))


def _fetch_latitude_template(
    api_key: str, project_id: Optional[str], version_uuid: Optional[str], document_path: str
) -> Dict[str, Any]:
    """
    Fetch template data from Latitude API v3

    Args:
        api_key: Latitude API key
        project_id: Project ID (optional)
        version_uuid: Version UUID (required for most operations)
        document_path: Path to the document/prompt

    Returns:
        dict: Template data from Latitude API

    Raises:
        ValueError: If the API request fails
    """
    # Set up headers for all requests
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Validate required parameters
    if not version_uuid:
        raise ValueError("Version UUID is required. Format: lat:version-uuid/document-path")

    # Build API URL using v3 structure
    if project_id:
        if document_path:
            # Get specific document
            url = f"https://gateway.latitude.so/api/v3/projects/{project_id}/versions/{version_uuid}/documents/{document_path}"
        else:
            # List all documents in version
            url = f"https://gateway.latitude.so/api/v3/projects/{project_id}/versions/{version_uuid}/documents"
    else:
        # Try without project ID - might work with some endpoints
        if document_path:
            # Try version-only endpoint (might exist)
            url = f"https://gateway.latitude.so/api/v3/versions/{version_uuid}/documents/{document_path}"
        else:
            # Try to list documents in version without project
            url = f"https://gateway.latitude.so/api/v3/versions/{version_uuid}/documents"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            return data

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Latitude API key")
        elif e.response.status_code == 404:
            if document_path:
                raise ValueError(f"Document not found: {document_path}")
            else:
                raise ValueError(f"Version not found: {version_uuid}")
        else:
            raise ValueError(f"Latitude API error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise ValueError(f"Failed to connect to Latitude API: {e}")
    except Exception as e:
        raise ValueError(f"Error loading template from Latitude: {e}")


def _create_llm_template(template_path: str, data: Dict[str, Any]) -> llm.Template:
    """
    Create LLM Template object from Latitude data

    Args:
        template_path: Original template path for naming
        data: Template data from Latitude API

    Returns:
        llm.Template: Configured template object
    """
    template_config = {
        "name": template_path,
    }

    # Extract prompt content
    if "content" in data:
        template_config["prompt"] = data["content"]
    elif "prompt" in data:
        template_config["prompt"] = data["prompt"]

    # Extract system prompt if available
    if "system" in data and data["system"]:
        template_config["system"] = data["system"]
    elif "system_prompt" in data and data["system_prompt"]:
        template_config["system"] = data["system_prompt"]

    # Extract suggested model if available
    if "model" in data and data["model"]:
        template_config["model"] = data["model"]
    elif "recommended_model" in data and data["recommended_model"]:
        template_config["model"] = data["recommended_model"]

    # Extract default parameters if available
    if "parameters" in data and isinstance(data["parameters"], dict):
        template_config["defaults"] = data["parameters"]
    elif "defaults" in data and isinstance(data["defaults"], dict):
        template_config["defaults"] = data["defaults"]

    # Extract model options if available
    if "model_config" in data and isinstance(data["model_config"], dict):
        template_config["options"] = data["model_config"]
    elif "options" in data and isinstance(data["options"], dict):
        template_config["options"] = data["options"]

    # Extract schema if available (for structured output)
    if "schema" in data and data["schema"]:
        template_config["schema_object"] = data["schema"]
    elif "json_schema" in data and data["json_schema"]:
        template_config["schema_object"] = data["json_schema"]

    return llm.Template(**template_config)
