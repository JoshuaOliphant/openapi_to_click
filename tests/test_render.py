"""Unit tests that exercise the real Jinja template (no client generation)."""

import click.testing

from openapi_to_cli import naming
from openapi_to_cli.render import build_context, default_template_dir, render_cli
from openapi_to_cli.spec import OpenAPISpec


def _render(spec_dict, client_module="my_client"):
    spec = OpenAPISpec(**spec_dict)
    context = build_context(spec, client_module)
    return render_cli(default_template_dir(), context), context


def test_naming_helpers():
    assert naming.tag_module(None) == "default"
    assert naming.tag_module(["Pet Store"]) == "pet_store"
    assert naming.endpoint_module("read_item__items__get", "get", "/") == (
        "read_item_items_get"
    )
    assert naming.option_flag("item_id") == "--item-id"
    assert naming.click_type_for({"type": "integer"}) == "click.INT"
    assert (
        naming.click_type_for({"anyOf": [{"type": "string"}, {"type": "null"}]})
        == "click.STRING"
    )


def test_rendered_cli_is_valid_python(valid_openapi_spec):
    source, _ = _render(valid_openapi_spec)
    # The whole point: the real template must compile.
    compile(source, "<generated cli.py>", "exec")


def test_imports_are_tag_aware(valid_openapi_spec):
    source, _ = _render(valid_openapi_spec)
    # Endpoints carry tags, so imports must NOT hardcode `api.default.`.
    assert "from my_client.api.items.read_item import sync_detailed" in source
    assert "from my_client.api.widgets.create_widget import sync_detailed" in source
    assert "api.default." not in source


def test_request_body_wired_with_model(valid_openapi_spec):
    source, context = _render(valid_openapi_spec)
    assert "from my_client.models import Widget" in source
    assert "--body" in source
    assert "Widget.from_dict(payload)" in source


def test_no_wildcard_model_import(valid_openapi_spec):
    source, _ = _render(valid_openapi_spec)
    assert "import *" not in source


def test_errors_render_as_clickexceptions(valid_openapi_spec):
    """Common runtime failures must surface as clean messages, not tracebacks."""
    source, _ = _render(valid_openapi_spec)
    # Bad JSON, unreadable file, and transport errors all become ClickExceptions.
    assert "--body is not valid JSON" in source
    assert "Could not read body file" in source
    assert "Request failed" in source
    # The HTTP call is wrapped so httpx errors don't escape as tracebacks.
    assert "_call(" in source


def test_generated_group_help_lists_commands(valid_openapi_spec):
    """Compile and load the generated module, then probe its Click group."""
    source, _ = _render(valid_openapi_spec)
    namespace: dict = {}
    exec(compile(_strip_client_imports(source), "<cli>", "exec"), namespace)
    result = click.testing.CliRunner().invoke(namespace["cli"], ["--help"])
    assert result.exit_code == 0
    assert "read-item" in result.output
    assert "create-widget" in result.output


def _strip_client_imports(source: str) -> str:
    """Drop generated client imports and stub the names they would have bound."""
    kept = [
        line for line in source.splitlines() if not line.startswith("from my_client")
    ]
    preamble = [
        "class _Stub:",
        "    def __init__(self, *a, **k): pass",
        "    def __call__(self, *a, **k): return self",
        "Client = AuthenticatedClient = Widget = _Stub",
        "read_item_op = create_widget_op = _Stub()",
    ]
    return "\n".join(preamble + kept)
