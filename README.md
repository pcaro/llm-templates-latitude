# llm-templates-latitude

[![CI](https://github.com/pcaro/llm-templates-latitude/workflows/CI/badge.svg)](https://github.com/pcaro/llm-templates-latitude/actions)
[![PyPI version](https://badge.fury.io/py/llm-templates-latitude.svg)](https://badge.fury.io/py/llm-templates-latitude)
[![codecov](https://codecov.io/gh/pcaro/llm-templates-latitude/branch/main/graph/badge.svg)](https://codecov.io/gh/pcaro/llm-templates-latitude)

Template loader for [LLM](https://llm.datasette.io/) that loads prompts from [Latitude](https://latitude.so/).

This plugin allows you to use prompts managed in Latitude as templates in LLM, giving you the best of both worlds: centralized prompt management in Latitude and flexible model execution with LLM.

## Installation

### From PyPI (when published)

```bash
llm install llm-templates-latitude
```

### Development Installation with uv

If you want to install from source or contribute to development:

```bash
git clone https://github.com/pcaro/llm-templates-latitude
cd llm-templates-latitude
uv sync
uv pip install -e .
```

## Configuration

Set your Latitude API key:

```bash
export LATITUDE_API_KEY="your-api-key"
```

Or configure it using LLM:

```bash
llm keys set latitude
# Enter: your-api-key
```

### SDK vs HTTP Client

The plugin supports two implementations that you can choose using different template prefixes:

- **`lat:`** or **`lat-http:`** - HTTP Client (default): Direct HTTP calls to Latitude API
- **`lat-sdk:`** - SDK Client: Uses the official Latitude Python SDK

### Using Different Implementations

Choose your implementation using the template prefix:

```bash
# HTTP Client (default) - both of these are equivalent
llm -t lat:99999/live/welcome-email -m gpt-4 "New user signed up"
llm -t lat-http:99999/live/welcome-email -m gpt-4 "New user signed up"

# SDK Client (requires latitude-sdk package)
llm -t lat-sdk:99999/live/welcome-email -m gpt-4 "New user signed up"
```

To use the SDK implementation, you need to install the SDK package:

```bash
# Install the latitude-sdk package
pip install latitude-sdk

# Then use the lat-sdk: prefix
llm -t lat-sdk:99999/live/welcome-email -m gpt-4 "input"
```

To check which implementation a prefix would use:

```python
import llm_templates_latitude

print(llm_templates_latitude.get_client_implementation("lat"))        # "http"
print(llm_templates_latitude.get_client_implementation("lat-http"))   # "http"
print(llm_templates_latitude.get_client_implementation("lat-sdk"))    # "sdk"
```

**Note**: Both implementations extract the same template fields and exclude potentially problematic fields like `model` and `provider` to avoid validation errors. The model should be specified using the `-m` flag instead of relying on Latitude's model recommendation.

### **SDK vs HTTP Behavior**

- **HTTP Client** (`lat:` or `lat-http:`): Directly queries the Latitude API v3 endpoint for the specific project/version/document combination
- **SDK Client** (`lat-sdk:`): Initializes with the project ID and version UUID context, then fetches the document. The SDK automatically handles version switching when you request different versions of prompts.

## Usage

### Basic Usage

Load a Latitude prompt as a template and use it with any LLM model:

```bash
# Use a Latitude prompt with GPT-4
llm -t lat:99999/live/welcome-email -m gpt-4 "New user John just signed up"

# Use with Claude
llm -t lat:99999/live/blog-writer -m claude-3.5-sonnet -p topic "AI development" "Write an article"

# Use with local models
llm -t lat:99999/live/code-reviewer -m llama2 < my-code.py
```

### Template Path Formats

**Important**: Latitude API v3 requires specific format with project ID, version UUID, and document path. Traditional path-based access is not supported.

```bash
# Full format with specific version: project-id/version-uuid/document-path
llm -t lat:99999/dc951f3b-a3d9-4ede-bff1-821e7b10c5e8/pcaro-random-number -m gpt-4 "Sumale 3"

# Use live version (recommended for latest): project-id/live/document-path
llm -t lat:99999/live/pcaro-random-number -m gpt-4 "Sumale 3"


```

**💡 How to find the required values**:

- **Project ID**: Numeric ID from Latitude project settings (e.g., `99999`)
- **Version**: Either `live` for the latest version, or the specific UUID (e.g., `dc951f3b-a3d9-4ede-bff1-821e7b10c5e8`)
- **Document Path**: Exact name of your prompt in Latitude (e.g., `pcaro-random-number`)

**✅ Recommended**: Use `live` for the current version of your prompts, or specific UUIDs when you need exact version control.

### With Parameters

If your Latitude prompt has parameters defined (using `{{variable}}` syntax), you can provide values using the `-p` flag:

```bash
# Latitude prompt: "Hello {{name}}, your score is {{score}}"
llm -t lat:99999/live/user-greeting -p name "Alice" -p score 95 -m gpt-4

# Use with specific version
llm -t lat:99999/dc951f3b-a3d9-4ede-bff1-821e7b10c5e8/user-greeting -p name "Alice" -p score 95 -m gpt-4

# Use with any model
llm -t lat:99999/live/email-template -p recipient_name "Bob" -p tone "formal" -m claude-3 "Meeting cancelled"
```

**Variable Syntax Conversion**: The plugin automatically converts Latitude's `{{variable}}` syntax to LLM's `$variable` syntax, so your existing Latitude prompts work seamlessly with LLM's parameter system.

### Save Templates Locally

You can save Latitude templates locally for faster access:

```bash
# Download and save locally
llm -t lat:99999/live/summarizer --save my-summarizer

# Use the saved template
llm -t my-summarizer -m gpt-4 "Content to summarize"
```

### Streaming Responses

Templates work with streaming just like regular LLM usage:

```bash
# HTTP Client
llm -t lat:99999/live/story-writer -m gpt-4 "Once upon a time..." --stream

# SDK Client
llm -t lat-sdk:99999/live/story-writer -m gpt-4 "Once upon a time..." --stream
```

## Template Features

The plugin automatically extracts from your Latitude prompts:

- **Prompt content**: Main prompt text with variables
- **Variable conversion**: Converts `{{variable}}` to `$variable` for LLM compatibility
- **System prompts**: If defined in Latitude (with variable conversion)
- **Default parameters**: Parameter defaults from Latitude
- **Model configuration**: Temperature, max tokens, etc. (excluding model/provider fields)
- **JSON schemas**: For structured output prompts
- **YAML frontmatter**: Automatically parsed and removed from prompt content

## Examples

### Content Generation

```bash
# Blog post writer (using live version) - HTTP Client
llm -t lat:12345/live/blog-writer -m gpt-4 -p topic "Python packaging" -p audience "developers"

# Blog post writer - SDK Client
llm -t lat-sdk:12345/live/blog-writer -m gpt-4 -p topic "Python packaging" -p audience "developers"

# Email templates (HTTP default)
llm -t lat:12345/live/customer-support -m claude-3 "Customer wants refund"
```

### Code Tasks

```bash
# Code review - HTTP Client
llm -t lat:12345/live/code-reviewer -m gpt-4 < pull-request.diff

# Code review - explicit HTTP
llm -t lat-http:12345/live/code-reviewer -m gpt-4 < pull-request.diff

# Documentation generator - SDK Client
llm -t lat-sdk:12345/live/doc-generator -m claude-3 -p language "Python" < my-function.py
```

### Data Analysis

```bash
# Data summarizer - HTTP Client
cat data.csv | llm -t lat:12345/live/data-summary -m gpt-4

# Report generator - SDK Client
llm -t lat-sdk:12345/live/quarterly-report -m claude-3 -p quarter "Q4 2023" -p metrics "revenue,users"
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

### Setup

```bash
git clone https://github.com/pcaro/llm-templates-latitude
cd llm-templates-latitude

# Install dependencies and create virtual environment
uv sync

# Install in development mode
uv pip install -e .
```

### Running Tests

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=llm_templates_latitude
```

### Code Formatting and Linting

```bash
# Format code
uv run black .

# Lint code
uv run ruff check --fix .

# Type checking
uv run mypy llm_templates_latitude.py
```

### Building

```bash
# Build distribution packages
uv build
```

### Creating a Release

This project uses automated publishing to PyPI via GitHub Actions. To create a new release:

1. **Update the version** using uv:

   ```bash
   # Check what the new version would be (dry run)
   uv version --dry-run --bump patch   # for bug fixes
   uv version --dry-run --bump minor   # for new features
   uv version --dry-run --bump major   # for breaking changes
   
   # Actually bump the version
   uv version --bump minor  # or patch/major as needed
   ```

2. **Commit and push** the version change:

   ```bash
   git add pyproject.toml
   git commit -m "Bump version to $(grep '^version = ' pyproject.toml | cut -d'"' -f2)"
   git push origin main
   ```

3. **Create and push a git tag**:

   ```bash
   # Use the version from pyproject.toml
   VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
   git tag v$VERSION
   git push origin v$VERSION
   ```

4. **Create a GitHub release**:
   - Go to https://github.com/pcaro/llm-templates-latitude/releases
   - Click "Create a new release"
   - Use tag `v$VERSION` (must match the git tag)
   - Add release notes describing changes
   - Click "Publish release"

   Or use GitHub CLI:

   ```bash
   VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
   gh release create v$VERSION \
     --title "v$VERSION" \
     --notes "Description of changes in this version"
   ```

5. **Automatic publishing**: GitHub Actions will automatically:
   - Run tests
   - Build the package
   - Publish to PyPI
   - Make it available via `llm install llm-templates-latitude`

#### Testing Releases

To test publishing before a real release, use TestPyPI:

```bash
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
git tag test-v$VERSION
git push origin test-v$VERSION
```

This will publish to https://test.pypi.org for verification.

## How It Works

1. **Template Request**: When you use `-t lat:project-id/version/prompt`, `-t lat-http:project-id/version/prompt`, or `-t lat-sdk:project-id/version/prompt`, the plugin calls Latitude's API
2. **Client Selection**: The plugin automatically selects the HTTP or SDK client based on the prefix you used
3. **Template Download**: Retrieves the prompt content, system prompt, and configuration from Latitude
4. **LLM Integration**: Creates an LLM template with the downloaded content and converted variables
5. **Model Execution**: LLM processes your input with the chosen model using the Latitude prompt

This gives you:

- ✅ Centralized prompt management in Latitude
- ✅ Version control and A/B testing of prompts
- ✅ Team collaboration on prompts
- ✅ Flexibility to use any model with LLM
- ✅ Local caching and offline usage
- ✅ Integration with LLM's ecosystem (logs, conversations, etc.)

## Author

Created by **Pablo Caro Revuelta** ([@pcaro](https://github.com/pcaro))

## License

Apache 2.0
