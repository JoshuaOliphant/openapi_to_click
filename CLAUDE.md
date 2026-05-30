# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenAPI → Click CLI Generator is a Python tool that generates a command-line
interface from an OpenAPI 3.x specification. It wraps openapi-python-client to
produce a typed API client, then renders a Click-based `cli.py` that exposes
every operation as a subcommand.

## Development Commands

**Package management (uv):**
```bash
uv sync          # install deps + dev tools (ruff, pyright, pytest)
uv build         # build sdist + wheel (hatchling backend)
```

**Running the generator** (the bundled template is used by default — no
`--template-path` needed):
```bash
uv run openapi-to-cli <OPENAPI_SPEC_PATH> <OUTPUT_PATH>
uv run openapi-to-cli test_spec.json ./output       # bundled example spec
uv run python -m openapi_to_cli test_spec.json ./output   # module form
```

**Quality gates (all run in CI):**
```bash
uv run pytest tests        # tests
uv run ruff check .        # lint
uv run ruff format --check .   # formatting
uv run pyright             # type-check
```

## Architecture

The package lives under `src/openapi_to_cli/` (src layout). The pipeline is
orchestrated by `cli.py:generate_cli` and split into focused modules:

| Module        | Responsibility                                                            |
| ------------- | ------------------------------------------------------------------------- |
| `spec.py`     | `OpenAPISpec` Pydantic model, file-format checks, `load_spec` (raises `SpecError`). |
| `client.py`   | Run openapi-python-client (subprocess), discover the client package, add `__init__.py`s, patch the generated `pyproject.toml` (raises `ClientGenerationError`). |
| `naming.py`   | Derive tag dirs / module names / command names / model classes by reusing **opc's own** `PythonIdentifier`, `snake_case`, `pascal_case`, `kebab_case` so names always match the generated client. |
| `render.py`   | `build_context` turns a spec into a template context; `render_cli` renders the Jinja template. `default_template_dir` resolves the bundled template via `importlib.resources`. |
| `cli.py`      | Click entry point (`generate_cli` / `main` console script).               |
| `templates/cli_template.jinja2` | The template for the generated CLI.                     |

### Generated CLI behavior

The generated `cli.py` provides one subcommand per operation, with:
- Typed Click options for each parameter (path params required by default).
- `--base-url` (defaults to the spec's first absolute `servers` URL; env
  `OPENAPI_CLI_BASE_URL`).
- `--token` → swaps `Client` for `AuthenticatedClient` (env `OPENAPI_CLI_TOKEN`).
- `--output {json,raw}` — pretty-printed parsed body or raw response bytes.
- `--body` for JSON request bodies (literal string or `@file`), deserialized into
  the generated model when the body is a `$ref`.
- Explicit model imports (no `from ... import *`).

## Conventions

- **Naming is delegated to opc utilities** (`naming.py`). Do not hand-roll
  snake_case/tag logic — it will drift from what openapi-python-client emits.
- **Endpoints are filed under their first tag** (matching opc's default, which
  does not set `generate_all_tags`). Untagged operations live under `default`.
- **Errors raise** (`SpecError`, `ClientGenerationError`) and are converted to
  `click.ClickException` at the CLI boundary, rather than logging + returning.

## Testing Strategy

`tests/` (run from repo root; package is importable as `openapi_to_cli`):
- `test_spec.py` — spec validation and loading.
- `test_render.py` — exercises the **real** Jinja template: builds a context,
  renders, and `compile()`s / executes the output. This is the regression guard
  the previous suite lacked (it used to stub the template).
- `test_generate.py` — full end-to-end pipeline **including the openapi-python-client
  subprocess**, asserting the generated `cli.py` compiles and has tag-aware imports.

`conftest.py` provides a realistic `valid_openapi_spec` fixture (tags + a `$ref`
request body) and a `write_spec` helper.

## Notes / Gotchas

- **openapi-python-client must be on PATH** — it's invoked as a subprocess.
  `client.py` checks `shutil.which` and raises a clear error if missing, so run
  inside `uv run` or an activated venv.
- **opc 0.28.x emits a Poetry-style `pyproject.toml`** (`[tool.poetry]`).
  `patch_pyproject` handles both that and the PEP 621 `[project]` array
  (used with `--meta pdm`).
- **Inline (non-`$ref`) request bodies** are accepted as `--body` JSON and
  passed through as a parsed dict — they are not coerced into a generated model,
  since opc derives those model names from the operation in a way that isn't
  reproduced here.

## CI & Environment

- Python 3.13+ (`requires-python = ">=3.13"`, pinned in `.python-version`).
- Dev deps under `[dependency-groups]` (PEP 735); `uv sync` installs them.
- `.github/workflows/pr-unit-tests.yml` runs lint, format check, type-check, and
  tests on every pull request.
