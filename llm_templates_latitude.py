"""
LLM template loader for Latitude - Load prompts from Latitude as LLM templates
"""

import os
from typing import Optional

import llm
from dotenv import load_dotenv

from lat import (
    LatitudeAPIError,
    LatitudeAuthenticationError, 
    LatitudeClient,
    LatitudeNotFoundError,
    extract_template_data,
    parse_template_path,
)

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
    try:
        # Get API key from environment or LLM keys
        api_key = _get_api_key()
        
        # Create Latitude client
        client = LatitudeClient(api_key)

        # Parse template path
        project_id, version_uuid, document_path = parse_template_path(template_path)

        # Load template from Latitude
        if document_path:
            # Get specific document
            if not project_id:
                raise ValueError("Project ID is required for document access. Use: project_id/version_uuid/document_path")
            latitude_data = client.get_document(project_id, version_uuid, document_path)
        else:
            # List documents (not implemented yet - would need different handling)
            raise ValueError("Document listing not yet implemented. Specify document path.")

        # Extract template configuration
        template_config = extract_template_data(latitude_data)
        template_config["name"] = template_path

        # Create LLM template
        return llm.Template(**template_config)
        
    except LatitudeAuthenticationError as e:
        raise ValueError(f"Authentication error: {e}")
    except LatitudeNotFoundError as e:
        raise ValueError(f"Not found: {e}")
    except LatitudeAPIError as e:
        raise ValueError(f"Latitude API error: {e}")
    except Exception as e:
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
