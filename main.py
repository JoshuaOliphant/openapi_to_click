import os
import click
import shutil
import subprocess
import yaml
import json
import logging
import sys
from jinja2 import Template, Environment, FileSystemLoader
from pydantic import BaseModel, ValidationError, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAPISpec(BaseModel):
    openapi: str
    info: dict
    paths: dict

    @field_validator('openapi')
    def check_openapi_version(cls, value):
        if not value.startswith("3."):
            raise ValueError("Only OpenAPI 3.x specifications are supported.")
        return value

@click.command()
@click.argument('openapi_spec_path', type=click.Path(exists=True))
@click.argument('output_path', type=click.Path())
@click.option('--template-path', type=click.Path(), default=None, help='Path to the directory containing the Jinja templates.')
def generate_cli(openapi_spec_path, output_path, template_path):
    """
    Generate a command-line interface (CLI) for an OpenAPI specification.

    Arguments:
    - OPENAPI_SPEC_PATH: Path to the OpenAPI specification file (YAML/JSON).
    - OUTPUT_PATH: Directory where the generated CLI will be saved.
    - TEMPLATE_PATH: Path to the directory containing the Jinja templates (optional).
    """
    # Ensure output directory exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Generate Python client from OpenAPI spec
    try:
        subprocess.run([
            "openapi-python-client",
            "generate",
            "--path",
            openapi_spec_path,
            "--output-path",
            output_path,
            "--overwrite"
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate client: {e}")
        return

    # Ensure output pyproject.toml has the click dependency
    pyproject_path = os.path.join(output_path, 'pyproject.toml')
    if os.path.exists(pyproject_path):
        with open(pyproject_path, 'r') as f:
            pyproject_content = f.readlines()

        with open(pyproject_path, 'w') as f:
            for line in pyproject_content:
                f.write(line)
                if line.startswith('[tool.poetry.dependencies]'):
                    # Add click dependency if not already present
                    if 'click' not in ''.join(pyproject_content):
                        f.write('click = "^8.1.7"\n')

    # Add __init__.py to make the directories packages
    client_package_name = [d for d in os.listdir(output_path) if d != '.ruff_cache' and os.path.isdir(os.path.join(output_path, d))][0]
    client_package_path = os.path.join(output_path, client_package_name)
    init_paths = [output_path, client_package_path]
    for path in init_paths:
        init_file = os.path.join(path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# This file makes this directory a package.")

    # Load OpenAPI spec to get endpoints
    try:
        with open(openapi_spec_path, 'r') as f:
            if openapi_spec_path.endswith('.yaml') or openapi_spec_path.endswith('.yml'):
                spec_data = yaml.safe_load(f)
            elif openapi_spec_path.endswith('.json'):
                spec_data = json.load(f)
            else:
                raise ValueError("Unsupported file format. Please provide a YAML or JSON file.")
    except Exception as e:
        logger.error(f"Failed to load OpenAPI spec: {e}")
        return

    # Validate OpenAPI spec using Pydantic
    try:
        spec = OpenAPISpec(**spec_data)
    except ValidationError as e:
        logger.error(f"OpenAPI specification validation failed: {e}")
        return

    # Parse paths from OpenAPI spec
    paths = spec.paths

    # Determine template path
    if not template_path:
        template_path = os.path.join(os.path.dirname(__file__), 'templates')

    # Load Click-based CLI template from an external file
    env = Environment(loader=FileSystemLoader(template_path))
    try:
        template = env.get_template('cli_template.jinja2')
    except Exception as e:
        logger.error(f"Failed to load template: {e}")
        return

    # Generate CLI code using Jinja template
    client_module = client_package_name
    try:
        # Create a dictionary for endpoint imports to render properly in the template
        endpoint_imports = []
        function_mappings = {}
        for path, methods in paths.items():
            for method, details in methods.items():
                operation_id = details.get('operationId', method).replace("__", "_")
                module_name = operation_id.lower()
                import_alias = f"{operation_id}_import"
                import_statement = f"from {client_module}.api.default.{module_name} import sync_detailed as {import_alias}"
                endpoint_imports.append(import_statement)
                function_mappings[operation_id] = import_alias
        cli_code = template.render(client_module=client_module, paths=paths, endpoint_imports=endpoint_imports, function_mappings=function_mappings)
    except Exception as e:
        logger.error(f"Failed to render CLI code: {e}")
        return

    # Write the generated CLI code to a file
    cli_file_path = os.path.join(output_path, 'cli.py')
    try:
        with open(cli_file_path, 'w') as cli_file:
            cli_file.write(cli_code)
    except Exception as e:
        logger.error(f"Failed to write CLI code to file: {e}")
        return

    click.echo(f"CLI generated at {cli_file_path}")

if __name__ == "__main__":
    generate_cli()
