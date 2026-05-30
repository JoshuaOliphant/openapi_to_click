"""Generate Click-based CLIs from OpenAPI 3.x specifications."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("openapi-to-cli")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0+dev"

from openapi_to_cli.spec import OpenAPISpec, load_spec

__all__ = ["OpenAPISpec", "load_spec", "__version__"]
