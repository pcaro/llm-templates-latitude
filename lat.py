"""
Latitude API client module

This module handles all interactions with the Latitude API.
It can be easily replaced with the official Latitude Python SDK in the future.
"""
import re
from typing import Any, Dict, Optional, Tuple

import httpx


class LatitudeAPIError(Exception):
    """Base exception for Latitude API errors"""
    pass


class LatitudeAuthenticationError(LatitudeAPIError):
    """Raised when API key is invalid"""
    pass


class LatitudeNotFoundError(LatitudeAPIError):
    """Raised when document/version is not found"""
    pass


class LatitudeClient:
    """Client for interacting with Latitude API v3"""
    
    def __init__(self, api_key: str):
        """
        Initialize Latitude client
        
        Args:
            api_key: Latitude API key
        """
        self.api_key = api_key
        self.base_url = "https://gateway.latitude.so/api/v3"
        
    def get_document(
        self, 
        project_id: str, 
        version_uuid: str, 
        document_path: str
    ) -> Dict[str, Any]:
        """
        Get a specific document from Latitude
        
        Args:
            project_id: Latitude project ID
            version_uuid: Version UUID
            document_path: Path to the document
            
        Returns:
            dict: Document data from Latitude API
            
        Raises:
            LatitudeAPIError: If the request fails
        """
        url = f"{self.base_url}/projects/{project_id}/versions/{version_uuid}/documents/{document_path}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                
                if response.status_code == 401:
                    raise LatitudeAuthenticationError("Invalid Latitude API key")
                elif response.status_code == 404:
                    raise LatitudeNotFoundError(f"Document not found: {document_path}")
                
                response.raise_for_status()
                return response.json()
                
        except (LatitudeAuthenticationError, LatitudeNotFoundError):
            # Re-raise these as-is
            raise
        except httpx.HTTPStatusError as e:
            raise LatitudeAPIError(f"Latitude API error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise LatitudeAPIError(f"Failed to connect to Latitude API: {e}")
        except Exception as e:
            raise LatitudeAPIError(f"Error loading document from Latitude: {e}")
    
    def list_documents(
        self, 
        project_id: str, 
        version_uuid: str
    ) -> Dict[str, Any]:
        """
        List all documents in a project version
        
        Args:
            project_id: Latitude project ID
            version_uuid: Version UUID
            
        Returns:
            dict: List of documents from Latitude API
            
        Raises:
            LatitudeAPIError: If the request fails
        """
        url = f"{self.base_url}/projects/{project_id}/versions/{version_uuid}/documents"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers)
                
                if response.status_code == 401:
                    raise LatitudeAuthenticationError("Invalid Latitude API key")
                elif response.status_code == 404:
                    raise LatitudeNotFoundError(f"Version not found: {version_uuid}")
                
                response.raise_for_status()
                return response.json()
                
        except (LatitudeAuthenticationError, LatitudeNotFoundError):
            # Re-raise these as-is
            raise
        except httpx.HTTPStatusError as e:
            raise LatitudeAPIError(f"Latitude API error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise LatitudeAPIError(f"Failed to connect to Latitude API: {e}")
        except Exception as e:
            raise LatitudeAPIError(f"Error loading documents from Latitude: {e}")


def parse_template_path(template_path: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Parse template path into project_id, version_uuid, and document_path
    
    Args:
        template_path: Must be one of:
            - 'project_id/version_uuid/document_path' - Full specification (recommended)
            - 'version_uuid/document_path' - Will try without project ID
            - 'project_id/version_uuid' - List all documents in version
    
    Returns:
        tuple: (project_id, version_uuid, document_path)
        
    Raises:
        ValueError: If template path format is invalid
    """
    parts = template_path.split("/")

    if len(parts) == 1:
        # Just version UUID - list all documents
        if is_uuid_like(parts[0]):
            return None, parts[0], ""
        else:
            raise ValueError(
                "Invalid format. Use: project_id/version_uuid/document_path"
            )
    elif len(parts) == 2:
        # Could be version_uuid/document_path or project_id/version_uuid
        if is_uuid_like(parts[0]):
            # version_uuid/document_path
            return None, parts[0], parts[1]
        elif is_uuid_like(parts[1]):
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
        
        if not is_uuid_like(version_uuid):
            raise ValueError(
                f"Invalid version UUID: {version_uuid}. "
                "Use: project_id/version_uuid/document_path"
            )
        
        return project_id, version_uuid, document_path
    else:
        raise ValueError("Invalid template path format")


def is_uuid_like(value: str) -> bool:
    """
    Check if a string looks like a UUID
    
    Args:
        value: String to check
        
    Returns:
        bool: True if it looks like a UUID
    """
    # Basic UUID pattern: 8-4-4-4-12 characters
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, value.lower()))


def extract_template_data(latitude_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract template configuration from Latitude API response
    
    Args:
        latitude_data: Raw response from Latitude API
        
    Returns:
        dict: Template configuration suitable for LLM Template
    """
    template_config = {}
    
    # Extract prompt content
    if "content" in latitude_data:
        template_config["prompt"] = latitude_data["content"]
    elif "prompt" in latitude_data:
        template_config["prompt"] = latitude_data["prompt"]
    
    # Extract system prompt if available
    if "system" in latitude_data and latitude_data["system"]:
        template_config["system"] = latitude_data["system"]
    elif "system_prompt" in latitude_data and latitude_data["system_prompt"]:
        template_config["system"] = latitude_data["system_prompt"]
    
    # Extract suggested model if available
    if "model" in latitude_data and latitude_data["model"]:
        template_config["model"] = latitude_data["model"]
    elif "recommended_model" in latitude_data and latitude_data["recommended_model"]:
        template_config["model"] = latitude_data["recommended_model"]
    
    # Extract default parameters if available
    if "parameters" in latitude_data and isinstance(latitude_data["parameters"], dict):
        template_config["defaults"] = latitude_data["parameters"]
    elif "defaults" in latitude_data and isinstance(latitude_data["defaults"], dict):
        template_config["defaults"] = latitude_data["defaults"]
    
    # Extract model options if available
    if "model_config" in latitude_data and isinstance(latitude_data["model_config"], dict):
        template_config["options"] = latitude_data["model_config"]
    elif "options" in latitude_data and isinstance(latitude_data["options"], dict):
        template_config["options"] = latitude_data["options"]
    
    # Extract schema if available (for structured output)
    if "schema" in latitude_data and latitude_data["schema"]:
        template_config["schema_object"] = latitude_data["schema"]
    elif "json_schema" in latitude_data and latitude_data["json_schema"]:
        template_config["schema_object"] = latitude_data["json_schema"]
    
    return template_config