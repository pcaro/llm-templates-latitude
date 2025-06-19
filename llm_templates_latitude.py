"""
LLM template loader for Latitude - Load prompts from Latitude as LLM templates
"""

import os

import llm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@llm.hookimpl
def register_template_loaders(register):
    """Register Latitude template loaders with LLM"""
    register(
        "lat", lambda path: latitude_template_loader(path, use_sdk=False)
    )  # Default (HTTP)
    register(
        "lat-http", lambda path: latitude_template_loader(path, use_sdk=False)
    )  # Explicit HTTP
    register(
        "lat-sdk", lambda path: latitude_template_loader(path, use_sdk=True)
    )  # SDK


def latitude_template_loader(template_path: str, use_sdk: bool = False) -> llm.Template:
    """
    Load a template from Latitude platform

    Args:
        template_path: Can be one of:
            - 'project_id/version_uuid/document_path' - Full path with project, version, and document
            - 'version_uuid/document_path' - Version and document (project determined automatically)
            - 'project_id/version_uuid' - Project and version (lists all documents)
        use_sdk: Whether to use the SDK implementation or HTTP client

    Returns:
        llm.Template: Template object with prompt content from Latitude

    Raises:
        ValueError: If API key is missing or template cannot be loaded
    """
    try:
        # Get API key from environment or LLM keys
        api_key = _get_api_key()

        # Import utilities first
        from utils import (
            extract_template_data,
            parse_template_path,
        )

        # Parse template path first
        project_id, version_uuid, document_path = parse_template_path(template_path)

        # Validate document path
        if not document_path:
            raise ValueError(
                "Document listing not yet implemented. Specify document path."
            )

        # Validate project_id is required for document access
        if not project_id:
            raise ValueError(
                "Project ID is required for document access. Use: project_id/version_uuid/document_path"
            )

        # Ensure version_uuid is not None for mypy
        if version_uuid is None:
            raise ValueError("Version UUID cannot be None")

        # Load template from appropriate client
        if use_sdk:
            try:
                from lat_sdk import LatitudeClient as SDKLatitudeClient

                # For SDK, we can pass project_id during initialization if available
                sdk_client = SDKLatitudeClient(api_key, project_id)
                latitude_data = sdk_client.get_document(
                    project_id, version_uuid, document_path
                )
            except ImportError:
                raise ValueError(
                    "SDK not available. Install with: pip install latitude-sdk"
                )
        else:
            from lat import LatitudeClient as HTTPLatitudeClient

            http_client = HTTPLatitudeClient(api_key)
            latitude_data = http_client.get_document(
                project_id, version_uuid, document_path
            )

        # Extract template configuration
        template_config = extract_template_data(latitude_data)
        template_config["name"] = template_path

        # Create LLM template
        return llm.Template(**template_config)

    except ValueError:
        # Re-raise ValueError (like "SDK not available") as-is
        raise
    except Exception as e:
        # Handle Latitude-specific errors if the exception classes are defined
        error_name = type(e).__name__
        if "Authentication" in error_name:
            raise ValueError(f"Authentication error: {e}")
        elif "NotFound" in error_name:
            raise ValueError(f"Not found: {e}")
        elif "LatitudeAPI" in error_name:
            raise ValueError(f"Latitude API error: {e}")
        else:
            raise ValueError(f"Error loading template: {e}")


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


def get_client_implementation(template_name: str = "lat") -> str:
    """
    Get the client implementation for a given template name

    Args:
        template_name: Template name prefix (lat, lat-http, lat-sdk)

    Returns:
        str: "sdk" for SDK implementation, "http" for HTTP client
    """
    if template_name.startswith("lat-sdk"):
        return "sdk"
    else:
        return "http"
