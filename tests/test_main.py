import pytest
import os
import tempfile
import shutil
import yaml
import json
from click.testing import CliRunner
from app.main import generate_cli, OpenAPISpec

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def valid_openapi_spec():
    """Create a valid OpenAPI 3.0 specification."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/test": {
                "get": {
                    "operationId": "test_endpoint",
                    "summary": "Test endpoint",
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        }
                    }
                }
            }
        }
    }

class TestOpenAPISpec:
    def test_valid_spec(self, valid_openapi_spec):
        """Test that a valid OpenAPI spec is accepted."""
        spec = OpenAPISpec(**valid_openapi_spec)
        assert spec.openapi == "3.0.0"
        assert spec.info["title"] == "Test API"
        assert "/test" in spec.paths

    def test_invalid_version(self):
        """Test that an invalid OpenAPI version is rejected."""
        invalid_spec = {
            "openapi": "2.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {}
        }
        with pytest.raises(ValueError, match="Only OpenAPI 3.x specifications are supported"):
            OpenAPISpec(**invalid_spec)

class TestCLIGenerator:
    def test_cli_generation_yaml(self, temp_dir, valid_openapi_spec):
        """Test CLI generation with YAML spec file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            # Create spec file
            spec_path = os.path.join(td, "openapi.yaml")
            with open(spec_path, 'w') as f:
                yaml.dump(valid_openapi_spec, f)

            # Create output directory
            output_dir = os.path.join(td, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Create template
            template_dir = os.path.join(td, "templates")
            os.makedirs(template_dir)
            with open(os.path.join(template_dir, "cli_template.jinja2"), "w") as f:
                f.write("# Generated CLI\n")

            result = runner.invoke(generate_cli, [
                spec_path,
                output_dir,
                "--template-path",
                template_dir
            ])

            assert result.exit_code == 0
            assert os.path.exists(os.path.join(output_dir, "cli.py"))
            assert "CLI generated at" in result.output

    def test_cli_generation_json(self, temp_dir, valid_openapi_spec):
        """Test CLI generation with JSON spec file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            # Create spec file
            spec_path = os.path.join(td, "openapi.json")
            with open(spec_path, 'w') as f:
                json.dump(valid_openapi_spec, f)

            # Create output directory
            output_dir = os.path.join(td, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Create template
            template_dir = os.path.join(td, "templates")
            os.makedirs(template_dir)
            with open(os.path.join(template_dir, "cli_template.jinja2"), "w") as f:
                f.write("# Generated CLI\n")

            result = runner.invoke(generate_cli, [
                spec_path,
                output_dir,
                "--template-path",
                template_dir
            ])

            assert result.exit_code == 0
            assert os.path.exists(os.path.join(output_dir, "cli.py"))
            assert "CLI generated at" in result.output

    def test_invalid_spec_path(self, temp_dir):
        """Test CLI generation with non-existent spec file."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            output_dir = os.path.join(td, "output")
            result = runner.invoke(generate_cli, ["nonexistent.yaml", output_dir])
            assert result.exit_code == 2  # Click's error code for file not found
            assert "does not exist" in result.output

    def test_unsupported_file_format(self, temp_dir):
        """Test CLI generation with unsupported file formats."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=temp_dir) as td:
            spec_path = os.path.join(td, "spec.txt")
            output_dir = os.path.join(td, "output")

            with open(spec_path, "w") as f:
                f.write("invalid content")

            result = runner.invoke(generate_cli, [spec_path, output_dir])
            assert result.exit_code == 1
            assert "Unsupported file format" in result.output

def test_output_directory_creation(temp_dir, valid_openapi_spec):
    """Test that the output directory is created if it doesn't exist."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=temp_dir) as td:
        # Create spec file
        spec_path = os.path.join(td, "openapi.yaml")
        with open(spec_path, 'w') as f:
            yaml.dump(valid_openapi_spec, f)

        # Create template
        template_dir = os.path.join(td, "templates")
        os.makedirs(template_dir)
        with open(os.path.join(template_dir, "cli_template.jinja2"), "w") as f:
            f.write("# Generated CLI\n")

        # Use a nested output directory that doesn't exist
        output_dir = os.path.join(td, "nonexistent", "output")

        result = runner.invoke(generate_cli, [
            spec_path,
            output_dir,
            "--template-path",
            template_dir
        ])

        assert result.exit_code == 0
        assert os.path.exists(output_dir)
        assert os.path.exists(os.path.join(output_dir, "cli.py"))
