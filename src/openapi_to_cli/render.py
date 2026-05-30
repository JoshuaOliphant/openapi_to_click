"""Build the template context from a spec and render the CLI source."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from openapi_to_cli import naming
from openapi_to_cli.spec import OpenAPISpec

TEMPLATE_NAME = "cli_template.jinja2"

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def default_template_dir() -> str:
    """Return the directory holding the template bundled with the package."""
    return str(files("openapi_to_cli") / "templates")


def _json_body_ref(operation: dict[str, Any]) -> str | None:
    """Return the ``$ref`` of an operation's JSON request body schema, if any."""
    content = operation.get("requestBody", {}).get("content", {})
    schema = content.get("application/json", {}).get("schema", {})
    ref = schema.get("$ref")
    return ref if isinstance(ref, str) else None


def _build_param(param: dict[str, Any]) -> dict[str, Any]:
    name = param["name"]
    return {
        "option": naming.option_flag(name),
        "pyname": naming.param_pyname(name),
        "required": bool(param.get("required", param.get("in") == "path")),
        "help_repr": repr(param.get("description", "") or ""),
        "click_type": naming.click_type_for(param.get("schema")),
    }


def build_context(spec: OpenAPISpec, client_module: str) -> dict[str, Any]:
    """Assemble everything the Jinja template needs to emit the CLI."""
    endpoints: list[dict[str, Any]] = []
    imports: list[str] = []
    model_imports: set[str] = set()
    seen_aliases: set[str] = set()

    for path, methods in spec.paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            operation_id = operation.get("operationId")
            func_name = naming.endpoint_module(operation_id, method, path)
            alias = f"{func_name}_op"
            # Guard against duplicate operation names producing clashing aliases.
            suffix = 2
            while alias in seen_aliases:
                alias = f"{func_name}_op{suffix}"
                suffix += 1
            seen_aliases.add(alias)

            module = naming.endpoint_module(operation_id, method, path)
            tag = naming.tag_module(operation.get("tags"))
            imports.append(
                f"from {client_module}.api.{tag}.{module} "
                f"import sync_detailed as {alias}"
            )

            body_ref = _json_body_ref(operation)
            body_model = naming.model_class_from_ref(body_ref) if body_ref else None
            if body_model:
                model_imports.add(body_model)

            summary = operation.get("summary") or operation.get("description") or ""
            endpoints.append(
                {
                    "command_name": naming.command_name(operation_id, method, path),
                    "func_name": func_name,
                    "import_alias": alias,
                    "doc_repr": repr(
                        f"{method.upper()} {path}"
                        + (f" — {summary}" if summary else "")
                    ),
                    "params": [
                        _build_param(p)
                        for p in operation.get("parameters", [])
                        if isinstance(p, dict) and "name" in p
                    ],
                    "has_body": body_ref is not None or "requestBody" in operation,
                    "body_model": body_model,
                }
            )

    for model in sorted(model_imports):
        imports.append(f"from {client_module}.models import {model}")

    return {
        "client_module": client_module,
        "api_title": spec.info.get("title", "API"),
        "default_base_url": spec.default_base_url,
        "imports": imports,
        "endpoints": endpoints,
    }


def render_cli(template_dir: str | Path, context: dict[str, Any]) -> str:
    """Render the CLI source from ``template_dir`` using ``context``."""
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(TEMPLATE_NAME)
    return template.render(**context)
