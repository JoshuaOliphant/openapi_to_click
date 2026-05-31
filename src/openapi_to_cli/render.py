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


def _resolve_param(param: dict[str, Any], components: dict[str, Any]) -> dict | None:
    """Resolve a (possibly ``$ref``) parameter object against components."""
    ref = param.get("$ref")
    if isinstance(ref, str):
        # e.g. "#/components/parameters/IdParam"
        node: Any = {"components": components}
        for part in ref.lstrip("#/").split("/"):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        param = node if isinstance(node, dict) else {}
    return param if "name" in param else None


def _operation_params(
    operation: dict[str, Any], shared: list, components: dict[str, Any]
) -> list[dict]:
    """Merge path-level and operation-level parameters, op-level winning.

    Parameters given as ``$ref`` to ``components/parameters`` are resolved so
    they are not silently dropped (which would make the command uncallable).
    """
    by_name: dict[str, dict] = {}
    for param in [*shared, *operation.get("parameters", [])]:
        if not isinstance(param, dict):
            continue
        resolved = _resolve_param(param, components)
        if resolved is not None:
            by_name[resolved["name"]] = resolved
    return [_build_param(p) for p in by_name.values()]


def _ensure_unique_names(endpoints: dict[tuple[str, str], dict[str, Any]]) -> None:
    """Assign collision-free func_name / import_alias / command_name in place.

    When two endpoints under different tags share a module name, suffix the
    later ones (with the tag, then a counter) so the generated defs, aliases,
    and Click command names stay unique.
    """
    used_funcs: set[str] = set()
    used_commands: set[str] = set()
    for (tag, module), ep in endpoints.items():
        func = module
        if func in used_funcs:
            func = f"{module}_{tag}"
            counter = 2
            while func in used_funcs:
                func = f"{module}_{tag}_{counter}"
                counter += 1
        used_funcs.add(func)
        ep["func_name"] = func
        ep["import_alias"] = f"{func}_op"

        command = ep["command_name"]
        if command in used_commands:
            command = f"{command}-{naming.kebab_case(tag)}"
            counter = 2
            while command in used_commands:
                command = f"{ep['command_name']}-{naming.kebab_case(tag)}-{counter}"
                counter += 1
        used_commands.add(command)
        ep["command_name"] = command


def build_context(spec: OpenAPISpec, client_module: str) -> dict[str, Any]:
    """Assemble everything the Jinja template needs to emit the CLI."""
    # Key endpoints by (tag, module): openapi-python-client collapses operations
    # that resolve to the same module into a single client function (last one
    # wins), so we must emit exactly one command per module to avoid shadowing
    # duplicate `def`s. Insertion order is preserved; later collisions overwrite.
    endpoints: dict[tuple[str, str], dict[str, Any]] = {}
    model_imports: set[str] = set()
    components = spec.components

    for path, methods in spec.paths.items():
        if not isinstance(methods, dict):
            continue
        shared_params = methods.get("parameters", [])
        for method, operation in methods.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            operation_id = operation.get("operationId")
            module = naming.endpoint_module(operation_id, method, path)
            tag = naming.tag_module(operation.get("tags"))

            body_ref = _json_body_ref(operation)
            body_model = naming.model_class_from_ref(body_ref) if body_ref else None

            summary = operation.get("summary") or operation.get("description") or ""
            endpoints[(tag, module)] = {
                "command_name": naming.command_name(operation_id, method, path),
                "tag": tag,
                "module": module,
                "doc_repr": repr(
                    f"{method.upper()} {path}" + (f" — {summary}" if summary else "")
                ),
                "params": _operation_params(operation, shared_params, components),
                "has_body": body_ref is not None or "requestBody" in operation,
                "body_model": body_model,
            }
            if body_model:
                model_imports.add(body_model)

    # The same module name can appear under different tags (e.g. operationId
    # "list" tagged both "pets" and "owners"), which would emit clashing
    # function defs, import aliases, and command names. Disambiguate each so
    # every command stays reachable.
    _ensure_unique_names(endpoints)

    imports = [
        f"from {client_module}.api.{ep['tag']}.{ep['module']} "
        f"import sync_detailed as {ep['import_alias']}"
        for ep in endpoints.values()
    ]
    for model in sorted(model_imports):
        imports.append(f"from {client_module}.models import {model}")

    return {
        "client_module": client_module,
        "api_title": spec.info.get("title", "API"),
        "default_base_url": spec.default_base_url,
        "imports": imports,
        "endpoints": list(endpoints.values()),
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
