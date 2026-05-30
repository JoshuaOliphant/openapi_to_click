import pytest

from openapi_to_cli.spec import OpenAPISpec, SpecError, load_spec


class TestOpenAPISpec:
    def test_valid_spec(self, valid_openapi_spec):
        spec = OpenAPISpec(**valid_openapi_spec)
        assert spec.openapi == "3.0.0"
        assert spec.info["title"] == "Test API"
        assert "/items/{item_id}" in spec.paths

    def test_default_base_url_from_servers(self, valid_openapi_spec):
        spec = OpenAPISpec(**valid_openapi_spec)
        assert spec.default_base_url == "https://api.example.com/v1"

    def test_relative_server_is_not_a_default_base_url(self):
        spec = OpenAPISpec.model_validate(
            {
                "openapi": "3.1.0",
                "info": {"title": "x", "version": "1"},
                "paths": {},
                "servers": [{"url": "/"}],
            }
        )
        assert spec.default_base_url is None

    def test_invalid_version(self):
        with pytest.raises(ValueError, match="Only OpenAPI 3.x"):
            OpenAPISpec(openapi="2.0.0", info={}, paths={})


class TestLoadSpec:
    def test_load_json(self, write_spec, valid_openapi_spec):
        spec = load_spec(write_spec(valid_openapi_spec, "json"))
        assert spec.info["title"] == "Test API"

    def test_load_yaml(self, write_spec, valid_openapi_spec):
        spec = load_spec(write_spec(valid_openapi_spec, "yaml"))
        assert spec.info["title"] == "Test API"

    def test_unsupported_format(self, tmp_path):
        bad = tmp_path / "spec.txt"
        bad.write_text("nope")
        with pytest.raises(SpecError, match="Unsupported file format"):
            load_spec(str(bad))

    def test_invalid_version_raises_spec_error(self, write_spec):
        with pytest.raises(SpecError, match="validation failed"):
            load_spec(write_spec({"openapi": "2.0", "info": {}, "paths": {}}))
