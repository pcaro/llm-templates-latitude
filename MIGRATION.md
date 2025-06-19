# Migration Guide: Using Official Latitude SDK

This document explains how to migrate from the current HTTP client implementation to the official Latitude Python SDK when it becomes available.

## Current Architecture

The plugin is structured with clear separation of concerns:

- **`llm_templates_latitude.py`**: LLM integration logic (template loading, registration)
- **`lat.py`**: Latitude API client implementation (HTTP calls, parsing, error handling)

## Migration Strategy

When the official Latitude Python SDK is available, only the `lat.py` module needs to be replaced while keeping the same interface.

### Interface to Maintain

The `lat.py` module provides these key functions that should be preserved:

```python
# Main client class
class LatitudeClient:
    def __init__(self, api_key: str)
    def get_document(self, project_id: str, version_uuid: str, document_path: str) -> Dict[str, Any]
    def list_documents(self, project_id: str, version_uuid: str) -> Dict[str, Any]

# Helper functions
def parse_template_path(template_path: str) -> Tuple[Optional[str], Optional[str], str]
def is_uuid_like(value: str) -> bool
def extract_template_data(latitude_data: Dict[str, Any]) -> Dict[str, Any]

# Exception classes
class LatitudeAPIError(Exception)
class LatitudeAuthenticationError(LatitudeAPIError)
class LatitudeNotFoundError(LatitudeAPIError)
```

### Migration Steps

1. **Install official SDK**:
   ```bash
   uv add latitude-sdk
   ```

2. **Replace `lat.py` implementation**:
   ```python
   # New lat.py using official SDK
   from latitude_sdk import Latitude
   
   class LatitudeClient:
       def __init__(self, api_key: str):
           self.client = Latitude(api_key)
       
       def get_document(self, project_id: str, version_uuid: str, document_path: str):
           # Use official SDK methods
           return self.client.documents.get(...)
   ```

3. **Update imports**:
   The main plugin file (`llm_templates_latitude.py`) doesn't need changes since it imports from `lat.py`.

4. **Test compatibility**:
   ```bash
   uv run pytest
   ```

### Benefits of This Architecture

- **Minimal disruption**: Only one file needs to change
- **Same interface**: No changes to how users invoke the plugin
- **Easy testing**: Can switch back and forth during migration
- **Clear separation**: LLM logic separate from Latitude API logic

### Current HTTP Implementation

The current implementation in `lat.py` uses:
- `httpx` for HTTP requests
- Manual API endpoint construction
- Custom error handling
- Direct JSON parsing

### Future SDK Implementation

The future implementation will use:
- Official Latitude SDK methods
- Built-in authentication handling
- SDK-provided error types
- Native data structures

### Compatibility Notes

When migrating, ensure:
1. **Return data format** matches current expectations
2. **Exception types** are mapped correctly
3. **Authentication** works with same API key
4. **All test cases** still pass

### Example Migration

**Current (HTTP client)**:
```python
def get_document(self, project_id: str, version_uuid: str, document_path: str):
    url = f"{self.base_url}/projects/{project_id}/versions/{version_uuid}/documents/{document_path}"
    response = httpx.get(url, headers=headers)
    return response.json()
```

**Future (Official SDK)**:
```python
def get_document(self, project_id: str, version_uuid: str, document_path: str):
    return self.sdk_client.projects.get_document(
        project_id=project_id,
        version_uuid=version_uuid, 
        document_path=document_path
    )
```

This architecture ensures a smooth transition when the official SDK becomes available.