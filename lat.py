"""
Latitude API client module

This module handles all interactions with the Latitude API.
It can be easily replaced with the official Latitude Python SDK in the future.
"""

from typing import Any, Dict

import httpx

from utils import (
    LatitudeAPIError,
    LatitudeAuthenticationError,
    LatitudeNotFoundError,
)


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
        self, project_id: str, version_uuid: str, document_path: str
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


# All utility functions have been moved to utils.py and are imported at the top
