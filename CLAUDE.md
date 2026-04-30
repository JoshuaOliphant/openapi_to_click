# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenAPI Click CLI Generator is a Python tool that automatically generates command-line interfaces from OpenAPI 3.x specifications. It wraps openapi-python-client and creates Click-based CLIs for easy API interaction.

## Development Commands

**Package Management (uses uv):**
```bash
# Install dependencies and create virtual environment
uv sync

# Build distribution packages
uv build
```

**Running the Generator (pass --template-path explicitly; the default is broken — see Known Gotchas):**
```bash
uv run python app/main.py <OPENAPI_SPEC_PATH> <OUTPUT_PATH> --template-path templates

# Example with bundled test spec
uv run python app/main.py test_spec.json ./output --template-path templates
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

The generator emits `output/cli.py` (our Click CLI) alongside the openapi-python-client tree (`output/<client_pkg>/{api,models}/` plus its own `pyproject.toml`).

### Important Conventions

**operationId Handling:**
- operationIds with double underscores (__) are converted to single underscores
- Example: "read_item__items__item_id__get" becomes "read_item_items_item_id_get"
- This happens in both import generation and function mapping (app/main.py:108, 113)

**Client Package Discovery:**
- The generator auto-detects the client package name from the first directory in output (excluding .ruff_cache)
- This name is used for imports in the generated CLI (app/main.py:67)

**Template Path Resolution:**
- Code default (app/main.py:154) is `app/templates/`, but the bundled template
  actually lives at repo-root `templates/cli_template.jinja2`. In practice you
  must pass `--template-path templates` when running from the repo root, or
  move the template to `app/templates/` to make the default work.
- The directory must contain `cli_template.jinja2` (file name is hard-coded).

## Known Gotchas

- **`update_pyproject_toml` is effectively a no-op (app/main.py:51-63).** It
  only inserts `click` under a `[tool.poetry.dependencies]` header, but the
  `openapi-python-client` versions used here emit a PEP 621 `[project]`
  table. The generated client's pyproject is left unchanged.
- **`openapi-python-client` is invoked as a subprocess, not a library**
  (app/main.py:37). It must be resolvable on PATH — running outside
  `uv run` (or an activated `.venv`) will fail with a confusing error.
- **Tests stub the template** (tests/test_main.py:77, 108, 159). Each test
  writes `# Generated CLI\n` over `cli_template.jinja2`, so the suite covers
  the orchestration pipeline but does NOT exercise the real Jinja template.
  Changes to `templates/cli_template.jinja2` are not test-covered.
- **`initialize_package_directories` picks the first non-`.ruff_cache`
  directory as the client package** (app/main.py:67). If the output dir has
  any other pre-existing subdirectory, the wrong one wins silently.
- **The generated `cli.py` does `from <client>.models import *`**
  (templates/cli_template.jinja2:6), which will collide with any imported
  symbol of the same name. Worth remembering before adding template imports.

## CI & Environment

- Python 3.13+ required (pyproject.toml `requires-python = ">=3.13"`, pinned
  in `.python-version`).
- Dev dependencies live under `[dependency-groups]` (PEP 735); `uv sync`
  installs the `dev` group by default.
- CI: `.github/workflows/pr-unit-tests.yml` runs `uv sync --locked` then
  `uv run pytest tests` on every pull request. No lint/type check stage.
- Tests import via `from app.main import ...` — must be invoked from repo root.

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
