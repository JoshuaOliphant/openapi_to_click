![CI](https://github.com/JoshuaOliphant/openapi_to_click/actions/workflows/pr-unit-tests.yml/badge.svg)

# OpenAPI → Click CLI Generator

Generate a ready-to-run [Click](https://click.palletsprojects.com/) command-line
interface from any OpenAPI 3.x specification. The generator wraps
[openapi-python-client](https://github.com/openapi-generators/openapi-python-client)
to produce a typed Python API client, then emits a `cli.py` that exposes every
operation as a subcommand.

## Features

- **One command per operation** — `operationId`s become Click subcommands with
  typed options derived from the spec (`integer` → `INT`, `boolean` → `BOOL`, …).
- **Tag-aware imports** — endpoints grouped under any tag are wired up correctly,
  not just the `default` tag.
- **Authentication** — pass `--token` (or set `OPENAPI_CLI_TOKEN`) to switch from
  `Client` to `AuthenticatedClient` automatically.
- **Request bodies** — JSON request bodies are accepted via `--body` (a literal
  JSON string or `@path/to/file.json`) and deserialized into the generated model.
- **Sensible defaults** — `--base-url` defaults to the spec's first absolute
  `servers` entry and honors `OPENAPI_CLI_BASE_URL`.
- **Readable output** — responses print as pretty JSON by default, or `--output raw`.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

```sh
uv sync
```

## Usage

```sh
uv run openapi-to-cli <OPENAPI_SPEC_PATH> <OUTPUT_PATH> [--template-path DIR]
```

| Argument            | Description                                                        |
| ------------------- | ----------------------------------------------------------------- |
| `OPENAPI_SPEC_PATH` | Path to the OpenAPI spec (YAML or JSON).                           |
| `OUTPUT_PATH`       | Directory where the client and `cli.py` are written.              |
| `--template-path`   | Optional Jinja template dir (defaults to the bundled template).    |

You can also run it as a module: `uv run python -m openapi_to_cli ...`.

### Example

```sh
uv run openapi-to-cli test_spec.json ./output
```

This generates the API client plus `./output/cli.py`. The bundled template is
used automatically — no `--template-path` required.

### Running the generated CLI

```sh
cd output
python cli.py --help                       # list every operation
python cli.py read-item-items-item-id-get --help
python cli.py read-item-items-item-id-get --item-id 7 --base-url https://api.example.com
```

Authenticated request with a JSON body:

```sh
python cli.py create-widget \
  --token "$TOKEN" \
  --base-url https://api.example.com \
  --body '{"name": "gadget"}'
```

## Customization

The CLI shape is driven by `src/openapi_to_cli/templates/cli_template.jinja2`.
Copy it elsewhere, edit it, and pass `--template-path` to use your version.

## Development

```sh
uv sync
uv run pytest tests        # tests (exercise the real template + opc pipeline)
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pyright             # type-check
```

## Building

```sh
uv build
```

## Versioning & Releases

This project follows [Semantic Versioning](https://semver.org/) and keeps a
[CHANGELOG.md](CHANGELOG.md) in [Keep a Changelog](https://keepachangelog.com/)
format. The version of record lives in `pyproject.toml`; `openapi_to_cli.__version__`
reads it back at runtime and powers `--version`.

To cut a release:

1. Move the relevant `## [Unreleased]` notes in `CHANGELOG.md` under a new
   `## [X.Y.Z]` heading and update the compare links at the bottom.
2. Bump `version` in `pyproject.toml` to `X.Y.Z`.
3. Commit, then tag and push:

   ```sh
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

Pushing a `vX.Y.Z` tag triggers `.github/workflows/release.yml`, which verifies
the tag matches the package version, builds the sdist + wheel, and publishes a
GitHub Release with the built artifacts attached.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Contributions are welcome! Open an issue or submit a pull request.
