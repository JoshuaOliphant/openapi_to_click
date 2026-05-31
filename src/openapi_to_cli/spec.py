"""Loading and validation of OpenAPI specifications."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError, field_validator

SUPPORTED_SUFFIXES = (".yaml", ".yml", ".json")


class SpecError(Exception):
    """Raised when a specification cannot be loaded or is invalid."""


class Server(BaseModel):
    url: str = ""
    description: str | None = None


class OpenAPISpec(BaseModel):
    """Minimal validated view of an OpenAPI 3.x document."""

    openapi: str
    info: dict[str, Any]
    paths: dict[str, Any]
    servers: list[Server] = []
    components: dict[str, Any] = {}

    @field_validator("openapi")
    @classmethod
    def check_openapi_version(cls, value: str) -> str:
        if not value.startswith("3."):
            raise ValueError("Only OpenAPI 3.x specifications are supported.")
        return value

    @property
    def default_base_url(self) -> str | None:
        """Return the first absolute server URL, if the spec declares one."""
        for server in self.servers:
            if server.url.startswith(("http://", "https://")):
                return server.url.rstrip("/")
        return None


def check_file_format(spec_path: str | Path) -> None:
    """Validate that the spec file has a supported extension."""
    if Path(spec_path).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise SpecError("Unsupported file format. Please provide a YAML or JSON file.")


def load_spec(spec_path: str | Path) -> OpenAPISpec:
    """Load and validate an OpenAPI specification from disk.

    Raises:
        SpecError: if the file cannot be read, parsed, or validated.
    """
    path = Path(spec_path)
    check_file_format(path)

    try:
        text = path.read_text()
    except OSError as exc:
        raise SpecError(f"Failed to read spec file: {exc}") from exc

    try:
        if path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise SpecError(f"Failed to parse spec file: {exc}") from exc

    if not isinstance(data, dict):
        raise SpecError("Spec file did not contain an OpenAPI document.")

    try:
        return OpenAPISpec(**data)
    except ValidationError as exc:
        raise SpecError(f"OpenAPI specification validation failed:\n{exc}") from exc
