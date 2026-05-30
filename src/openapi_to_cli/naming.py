"""Name derivation helpers.

These mirror the conventions used by ``openapi-python-client`` so the imports
and call signatures emitted into the generated CLI line up with the client code
it actually produces. We reuse opc's own utilities rather than reimplementing
(and drifting from) its sanitisation rules.
"""

from __future__ import annotations

from openapi_python_client.utils import (
    PythonIdentifier,
    kebab_case,
    pascal_case,
    snake_case,
)

# Map OpenAPI primitive types onto Click parameter types.
_CLICK_TYPES = {
    "integer": "click.INT",
    "number": "click.FLOAT",
    "boolean": "click.BOOL",
    "string": "click.STRING",
}


def tag_module(tags: list[str] | None) -> str:
    """Return the ``api/<module>`` directory name openapi-python-client uses.

    By default opc files an endpoint under its *first* tag only, falling back to
    ``default`` when the operation is untagged.
    """
    tag = (tags or ["default"])[0]
    return str(PythonIdentifier(value=tag, prefix="tag"))


def endpoint_module(operation_id: str | None, method: str, path: str) -> str:
    """Return the endpoint module/function name opc generates for an operation."""
    base = operation_id or f"{method}_{path}"
    return snake_case(base)


def command_name(operation_id: str | None, method: str, path: str) -> str:
    """Return the kebab-cased Click command name for an operation."""
    return kebab_case(operation_id or f"{method}_{path}")


def param_pyname(name: str) -> str:
    """Return the Python identifier opc uses for a parameter argument."""
    return str(PythonIdentifier(value=name, prefix="field"))


def model_class_from_ref(ref: str) -> str:
    """Return the model class name opc generates for a ``$ref`` schema."""
    return str(pascal_case(ref.rstrip("/").split("/")[-1]))


def option_flag(name: str) -> str:
    """Return the ``--kebab-case`` Click option flag for a parameter name."""
    return f"--{kebab_case(name)}"


def click_type_for(schema: dict | None) -> str | None:
    """Return the ``click.<TYPE>`` token for a parameter schema, if known.

    Handles the OpenAPI 3.1 ``anyOf`` nullable idiom by picking the first
    concrete (non-``null``) type.
    """
    if not schema:
        return None
    schema_type = schema.get("type")
    if schema_type is None:
        for sub in schema.get("anyOf", []) or schema.get("oneOf", []):
            if isinstance(sub, dict) and sub.get("type") not in (None, "null"):
                schema_type = sub["type"]
                break
    return _CLICK_TYPES.get(schema_type) if schema_type else None
