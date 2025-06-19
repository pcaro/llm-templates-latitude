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

## Usage

### Basic Usage

Load a Latitude prompt as a template and use it with any LLM model:

```bash
# Use a Latitude prompt with GPT-4
llm -t lat:my-project/welcome-email -m gpt-4 "New user John just signed up"

# Use with Claude
llm -t lat:my-project/blog-writer -m claude-3.5-sonnet -p topic "AI development" "Write an article"

# Use with local models
llm -t lat:code-reviewer -m llama2 < my-code.py
```

### Template Path Formats

**Important**: Latitude API v3 requires specific format with project ID, version UUID, and document path. Traditional path-based access is not supported.

```bash
# Full format (recommended): project-id/version-uuid/document-path
llm -t lat:19228/dc951f3b-a3d9-4ede-bff1-821e7b10c5e8/pcaro-random-number -m gpt-4 "Sumale 3"

# Version and document (tries without project ID):
llm -t lat:dc951f3b-a3d9-4ede-bff1-821e7b10c5e8/pcaro-random-number -m gpt-4 "input"

# List documents in version:
llm -t lat:19228/dc951f3b-a3d9-4ede-bff1-821e7b10c5e8 -m gpt-4 "input"
```

**💡 How to find the required values**:
- **Project ID**: Numeric ID from Latitude project settings (e.g., `19228`)
- **Version UUID**: UUID of the prompt version in Latitude (e.g., `dc951f3b-a3d9-4ede-bff1-821e7b10c5e8`)
- **Document Path**: Exact name of your prompt in Latitude (e.g., `pcaro-random-number`)

**❌ Not supported**: Global paths like `PS - Site Selection/pcaro-random-number` are not available in API v3.

### With Parameters

If your Latitude prompt has parameters defined, you can override them:

```bash
llm -t lat:email-template -p recipient_name "Alice" -p tone "formal" "Meeting cancelled"
```

### Save Templates Locally

You can save Latitude templates locally for faster access:

```bash
# Download and save locally
llm -t lat:my-project/summarizer --save my-summarizer

# Use the saved template
llm -t my-summarizer -m gpt-4 "Content to summarize"
```

### Streaming Responses

Templates work with streaming just like regular LLM usage:

```bash
llm -t lat:story-writer -m gpt-4 "Once upon a time..." --stream
```

## Template Features

The plugin automatically extracts from your Latitude prompts:

- **Prompt content**: Main prompt text with variables
- **System prompts**: If defined in Latitude
- **Default parameters**: Parameter defaults from Latitude
- **Model recommendations**: Suggested model from Latitude
- **Model configuration**: Temperature, max tokens, etc.
- **JSON schemas**: For structured output prompts

## Examples

### Content Generation

```bash
# Blog post writer
llm -t lat:content/blog-writer -m gpt-4 -p topic "Python packaging" -p audience "developers"

# Email templates
llm -t lat:emails/customer-support -m claude-3 "Customer wants refund"
```

### Code Tasks

```bash
# Code review
llm -t lat:dev/code-reviewer -m gpt-4 < pull-request.diff

# Documentation generator
llm -t lat:dev/doc-generator -m claude-3 -p language "Python" < my-function.py
```

### Data Analysis

```bash
# Data summarizer
cat data.csv | llm -t lat:analysis/data-summary -m gpt-4

# Report generator
llm -t lat:reports/quarterly -m claude-3 -p quarter "Q4 2023" -p metrics "revenue,users"
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

1. **Update the version** in `pyproject.toml`:
   ```toml
   version = "0.1.2"  # Increment as needed
   ```

2. **Commit and push** the version change:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.1.2"
   git push origin main
   ```

3. **Create and push a git tag**:
   ```bash
   git tag v0.1.2
   git push origin v0.1.2
   ```

4. **Create a GitHub release**:
   - Go to https://github.com/pcaro/llm-templates-latitude/releases
   - Click "Create a new release"
   - Use tag `v0.1.2` (must match the git tag)
   - Add release notes describing changes
   - Click "Publish release"

   Or use GitHub CLI:
   ```bash
   gh release create v0.1.2 \
     --title "v0.1.2" \
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
git tag test-v0.1.2
git push origin test-v0.1.2
```

This will publish to https://test.pypi.org for verification.

## How It Works

1. **Template Request**: When you use `-t lat:project/prompt`, the plugin calls Latitude's API
2. **Template Download**: Retrieves the prompt content, system prompt, and configuration
3. **LLM Integration**: Creates an LLM template with the downloaded content
4. **Model Execution**: LLM processes your input with the chosen model using the Latitude prompt

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
