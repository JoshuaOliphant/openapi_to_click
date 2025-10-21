# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenAPI Click CLI Generator is a Python tool that automatically generates command-line interfaces from OpenAPI 3.x specifications. It wraps openapi-python-client and creates Click-based CLIs for easy API interaction.

## Development Commands

**Package Management (uses uv):**
```bash
# Install dependencies and create virtual environment
uv sync

# Activate virtual environment
source .venv/bin/activate

# Build distribution packages
uv build
```

**Running the Generator:**
```bash
# Run the CLI generator
uv run python app/main.py <OPENAPI_SPEC_PATH> <OUTPUT_PATH> [--template-path TEMPLATE_PATH]

# Example with test spec
uv run python app/main.py test_spec.json ./output
```

**Testing:**
```bash
# Run all tests
uv run pytest tests

# Run a specific test file
uv run pytest tests/test_main.py

# Run a specific test
uv run pytest tests/test_main.py::TestOpenAPISpec::test_valid_spec

# Run with verbose output
uv run pytest -v tests
```

## Architecture

### Core Generation Pipeline

The CLI generation follows this flow (app/main.py:129-169):

1. **Validation** - Check file format (YAML/JSON) and validate OpenAPI 3.x spec using Pydantic model
2. **Client Generation** - Call openapi-python-client to generate Python API client
3. **Package Setup** - Add __init__.py files and update pyproject.toml
4. **Template Rendering** - Generate CLI code using Jinja2 template
5. **Output** - Write cli.py to output directory

### Key Components

**OpenAPISpec Model (app/main.py:15-24):**
- Pydantic model that validates OpenAPI specs
- Ensures only OpenAPI 3.x specifications are supported
- Validates required fields: openapi, info, paths

**CLI Template (templates/cli_template.jinja2):**
- Generates Click-based CLI with commands for each API endpoint
- Creates dynamic imports from the generated client package
- Maps operationId to CLI command functions
- Handles both Client and AuthenticatedClient scenarios

**Template Rendering (app/main.py:98-123):**
- Extracts operationId from each path/method combination
- Generates import statements for each endpoint module
- Creates function mappings to connect CLI commands to client functions
- Template expects: client_module, paths, endpoint_imports, function_mappings

### Generated Output Structure

When the generator runs, it creates:
```
output/
├── pyproject.toml (from openapi-python-client)
├── {client_package_name}/ (auto-named from spec)
│   ├── __init__.py
│   ├── api/
│   │   └── default/
│   │       └── {operation_id}.py (one per endpoint)
│   └── models/
└── cli.py (Click CLI - our generated code)
```

### Important Conventions

**operationId Handling:**
- operationIds with double underscores (__) are converted to single underscores
- Example: "read_item__items__item_id__get" becomes "read_item_items_item_id_get"
- This happens in both import generation and function mapping (app/main.py:108, 113)

**Client Package Discovery:**
- The generator auto-detects the client package name from the first directory in output (excluding .ruff_cache)
- This name is used for imports in the generated CLI (app/main.py:67)

**Template Path Resolution:**
- If --template-path not provided, defaults to app/templates/ directory
- Template must contain cli_template.jinja2 (app/main.py:154)

## Testing Strategy

The test suite (tests/test_main.py) uses:
- Click's CliRunner for CLI testing
- Temporary directories for isolated filesystem operations
- Fixtures for valid OpenAPI specs
- Both YAML and JSON format testing

Tests cover:
- OpenAPI spec validation
- CLI generation with YAML/JSON specs
- Invalid file paths and formats
- Automatic output directory creation
- Template rendering
