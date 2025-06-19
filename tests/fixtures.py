"""Test fixtures and utilities for llm-templates-latitude tests"""

import json
from typing import Dict, Any, Optional


def create_mock_latitude_response(
    content: str = "Test prompt content",
    system: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    model_config: Optional[Dict[str, Any]] = None,
    schema: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock Latitude API response for testing
    
    Args:
        content: Prompt content
        system: System prompt
        parameters: Default parameters
        model_config: Model configuration
        schema: JSON schema for structured output
        **kwargs: Additional fields
        
    Returns:
        dict: Mock Latitude response
    """
    response = {"content": content}
    
    if system:
        response["system"] = system
    if parameters:
        response["parameters"] = parameters
    if model_config:
        response["model_config"] = model_config
    if schema:
        response["schema"] = schema
        
    # Add any additional fields
    response.update(kwargs)
    
    return response


def create_mock_sdk_response(
    content: str = "Test prompt content",
    config: Optional[Dict[str, Any]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a mock Latitude SDK response for testing
    
    SDK responses have a slightly different structure than HTTP API responses
    
    Args:
        content: Prompt content
        config: Configuration (maps to model_config in HTTP)
        parameters: Default parameters
        **kwargs: Additional fields like uuid, path, provider
        
    Returns:
        dict: Mock SDK response
    """
    response = {
        "uuid": kwargs.get("uuid", "550e8400-e29b-41d4-a716-446655440000"),
        "path": kwargs.get("path", "test-prompt"),
        "content": content,
    }
    
    if config:
        response["config"] = config
    if parameters:
        response["parameters"] = parameters
        
    # Add common SDK fields
    if "provider" in kwargs:
        response["provider"] = kwargs["provider"]
        
    return response


def create_prompt_with_frontmatter(
    prompt_content: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a prompt with YAML frontmatter
    
    Args:
        prompt_content: The actual prompt content
        provider: Provider name (e.g., 'openai')
        model: Model name (e.g., 'gpt-4')
        config: Configuration dict
        metadata: Additional metadata
        
    Returns:
        str: Prompt with YAML frontmatter
    """
    frontmatter_lines = ["---"]
    
    if provider:
        frontmatter_lines.append(f"provider: {provider}")
    if model:
        frontmatter_lines.append(f"model: {model}")
    if config:
        frontmatter_lines.append("config:")
        for key, value in config.items():
            frontmatter_lines.append(f"  {key}: {value}")
    if metadata:
        frontmatter_lines.append("metadata:")
        for key, value in metadata.items():
            frontmatter_lines.append(f"  {key}: {value}")
            
    frontmatter_lines.append("---")
    frontmatter_lines.append("")  # Empty line after frontmatter
    frontmatter_lines.append(prompt_content)
    
    return "\n".join(frontmatter_lines)


def create_template_config(
    prompt: str = "Test prompt",
    system: Optional[str] = None,
    defaults: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
    schema_object: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a template configuration dict suitable for llm.Template
    
    Args:
        prompt: Main prompt text
        system: System prompt
        defaults: Default parameter values
        options: Model options (temperature, etc.)
        schema_object: JSON schema
        **kwargs: Additional template fields
        
    Returns:
        dict: Template configuration
    """
    config = {"prompt": prompt}
    
    if system:
        config["system"] = system
    if defaults:
        config["defaults"] = defaults
    if options:
        config["options"] = options
    if schema_object:
        config["schema_object"] = schema_object
        
    config.update(kwargs)
    
    return config


# Sample test data
SAMPLE_PROMPTS = {
    "simple": "Generate a random number between 1 and 100",
    "with_parameters": "Hello {{name}}, welcome to {{company}}!",
    "with_system": {
        "content": "Summarize this text: {{input}}",
        "system": "You are a helpful summarization assistant."
    },
    "with_frontmatter": create_prompt_with_frontmatter(
        "Generate a creative story",
        provider="openai",
        model="gpt-4",
        config={"temperature": 0.9, "max_tokens": 1000}
    ),
    "complex": create_mock_latitude_response(
        content="Analyze {{data}} and provide insights",
        system="You are a data analyst",
        parameters={"data": "sample data"},
        model_config={"temperature": 0.5, "top_p": 0.95},
        schema={"type": "object", "properties": {"insights": {"type": "array"}}}
    )
}

SAMPLE_UUIDS = [
    "550e8400-e29b-41d4-a716-446655440000",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "dc951f3b-a3d9-4ede-bff1-821e7b10c5e8"
]

SAMPLE_PROJECT_IDS = ["12345", "99999", "20001"]

SAMPLE_DOCUMENT_PATHS = [
    "simple-prompt",
    "marketing/email-template",
    "dev/code-reviewer",
    "pcaro-random-number"
]