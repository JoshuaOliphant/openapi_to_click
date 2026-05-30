import json

import pytest
import yaml


@pytest.fixture
def valid_openapi_spec():
    """A small but realistic OpenAPI 3.x document with a tag and a request body."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com/v1"}],
        "paths": {
            "/items/{item_id}": {
                "get": {
                    "operationId": "read_item",
                    "summary": "Read an item",
                    "tags": ["items"],
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "q",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/widgets": {
                "post": {
                    "operationId": "create_widget",
                    "summary": "Create a widget",
                    "tags": ["widgets"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Widget"}
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            },
        },
        "components": {
            "schemas": {
                "Widget": {
                    "type": "object",
                    "title": "Widget",
                    "properties": {"name": {"type": "string"}},
                }
            }
        },
    }


@pytest.fixture
def write_spec(tmp_path):
    """Return a helper that writes a spec dict to disk in YAML or JSON."""

    def _write(spec, fmt="json"):
        path = tmp_path / f"openapi.{fmt}"
        if fmt in ("yaml", "yml"):
            path.write_text(yaml.dump(spec))
        else:
            path.write_text(json.dumps(spec))
        return str(path)

    return _write
