# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-02

First properly released version. Restructures the project into an installable
package and makes the generated CLI usable in practice.

### Added
- `openapi-to-cli` console-script entry point and `python -m openapi_to_cli`.
- Bundled Jinja template resolved via `importlib.resources`, so the default
  template works without `--template-path`.
- Generated CLI: typed Click options per parameter, `--token`
  (`AuthenticatedClient`), `--base-url` with `OPENAPI_CLI_BASE_URL` / `servers`
  default, `--body` for JSON request bodies (literal or `@file`), and
  `--output {json,raw}`.
- `--version` on both the generator and every generated CLI.
- ruff (lint + format) and pyright; CI now runs lint, format check, type-check,
  and tests.
- `docs/TESTING.md`: a testing guide and torture-spec checklist for future work
  on the generator.

### Changed
- Restructured from a flat `app/main.py` script into a `src/openapi_to_cli/`
  package split into focused modules (`spec`, `client`, `naming`, `render`, `cli`).
- Naming is delegated to openapi-python-client's own utilities so generated
  imports and call signatures always match the client it produces.
- Tests now exercise the real Jinja template and the full end-to-end pipeline
  (previously the template was stubbed and never tested).

### Fixed
- Tag-aware imports: endpoints are filed under `api/<tag>/...` instead of a
  hardcoded `api.default.`, so tagged operations resolve correctly.
- Reliable client-package discovery (locate the directory containing
  `client.py` rather than "the first directory").
- `patch_pyproject` actually adds `click` now, handling both the Poetry-style
  table opc emits and the PEP 621 array.
- Errors raise (`SpecError`, `ClientGenerationError`) and surface as clean
  `click.ClickException` messages instead of being logged and swallowed.
- Generated CLIs report common runtime failures as clean one-line errors
  instead of Python tracebacks: an unreachable server / transport error, a
  malformed `--body` JSON value, and an unreadable `@file` body all surface as
  `Error: ...` with a non-zero exit.
- Reserved-word and leading-digit names now match openapi-python-client exactly.
  An `operationId` like `import` is escaped to `import_` (was emitting an invalid
  `from ... import import ...`), and parameters like `2fa` map to `field_2fa`.
- `$ref` parameters (`#/components/parameters/...`) are resolved instead of being
  silently dropped — previously the generated command omitted the argument and
  the client call raised `TypeError`.
- Path-level (shared) parameters are merged into every operation under that path.
- Operations that collide on a generated name are handled: duplicates that opc
  collapses into one client module now emit a single command, and the same
  `operationId` under different tags gets distinct, reachable commands.

## [0.1.0]

Initial prototype (never tagged). Generated a Click CLI from an OpenAPI spec
using a flat `app/main.py` script and an external Jinja template.

[Unreleased]: https://github.com/JoshuaOliphant/openapi_to_click/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/JoshuaOliphant/openapi_to_click/releases/tag/v0.2.0
