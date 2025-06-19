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
        template_path: Format should be 'project_id/prompt_path'
                      or just 'prompt_path' for default project

    Returns:
        llm.Template: Template object with prompt content from Latitude

    Raises:
        ValueError: If API key is missing or template cannot be loaded
    """
    # Get API key from environment or LLM keys
    api_key = _get_api_key()

    # Parse template path
    project_id, prompt_path = _parse_template_path(template_path)

    # Load template from Latitude
    template_data = _fetch_latitude_template(api_key, project_id, prompt_path)

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


def _parse_template_path(template_path: str) -> tuple[Optional[str], str]:
    """
    Parse template path into project_id and prompt_path

    Args:
        template_path: Either 'project_id/prompt_path' or just 'prompt_path'

    Returns:
        tuple: (project_id, prompt_path)
    """
    parts = template_path.split("/", 1)

    if len(parts) == 1:
        # Just prompt path, use default project
        return None, parts[0]
    else:
        # project_id/prompt_path format
        return parts[0], parts[1]


def _fetch_latitude_template(
    api_key: str, project_id: Optional[str], prompt_path: str
) -> Dict[str, Any]:
    """
    Fetch template data from Latitude API

    Args:
        api_key: Latitude API key
        project_id: Project ID (optional, uses default if None)
        prompt_path: Path to the prompt within the project

    Returns:
        dict: Template data from Latitude API

    Raises:
        ValueError: If the API request fails
    """
    # Build API URL
    if project_id:
        url = f"https://gateway.latitude.so/api/v1/projects/{project_id}/prompts/{prompt_path}"
    else:
        url = f"https://gateway.latitude.so/api/v1/prompts/{prompt_path}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

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
            raise ValueError(f"Prompt not found: {prompt_path}")
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
