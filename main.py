import os
import click
import yaml
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, ValidationError, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Parameter:
    """Represents an API endpoint parameter."""
    name: str
    description: str
    required: bool
    type: str
    default: Any = None

@dataclass
class Operation:
    """Represents an API operation/endpoint."""
    method: str
    path: str
    tag: str
    summary: str
    description: str
    snake_case_name: str
    path_parameters: List[Parameter]
    query_parameters: List[Parameter]
    body_required: bool

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
def generate_cli(openapi_spec_path, output_path, template_path=None):
    """Generate a command-line interface (CLI) for an OpenAPI specification."""
    click.echo(f"Generating {output_path}")

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

    # Extract operations
    operations = extract_operations(spec_data)
    
    # Generate package name
    package_name = spec_data['info']['title'].lower().replace(' ', '_').replace('-', '_') + '_client'
    
    # If no template path is provided, use the default templates directory
    if template_path is None:
        template_path = os.path.join(os.path.dirname(__file__), "templates")

    # Set up Jinja environment
    env = Environment(loader=FileSystemLoader(template_path))
    try:
        template = env.get_template('cli_template.jinja2')
    except Exception as e:
        logger.error(f"Failed to load template: {e}")
        return

    # Create the output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Generate the CLI script
    output_file = os.path.join(output_path, "cli.py")

    try:
        # Render the CLI script
        cli_code = template.render(
            package_name=package_name,
            operations=operations
        )
        
        # Write the generated code
        with open(output_file, "w") as f:
            f.write(cli_code)
    except Exception as e:
        logger.error(f"Failed to generate CLI: {e}")
        return

    click.echo(f"CLI generated at {output_file}")

def snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    import re
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()

def get_type_for_schema(schema: Dict[str, Any]) -> str:
    """Convert OpenAPI type to Python type."""
    type_map = {
        'integer': 'int',
        'number': 'float',
        'string': 'str',
        'boolean': 'bool'
    }
    return type_map.get(schema.get('type', 'string'), 'str')

def extract_operations(spec: Dict[str, Any]) -> List[Operation]:
    """Extract operations from OpenAPI specification."""
    operations = []
    
    for path, path_item in spec['paths'].items():
        for method, operation in path_item.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                # Extract parameters
                parameters = operation.get('parameters', [])
                path_params = []
                query_params = []
                
                for param in parameters:
                    param_obj = Parameter(
                        name=param['name'],
                        description=param.get('description', ''),
                        required=param.get('required', False),
                        type=get_type_for_schema(param['schema']),
                        default=param.get('schema', {}).get('default')
                    )
                    
                    if param['in'] == 'path':
                        path_params.append(param_obj)
                    elif param['in'] == 'query':
                        query_params.append(param_obj)
                
                # Create operation object
                op = Operation(
                    method=method,
                    path=path,
                    tag='default',  # You might want to extract this from operation tags
                    summary=operation.get('summary', ''),
                    description=operation.get('description', ''),
                    snake_case_name=snake_case(path.strip('/').replace('/', '_')),
                    path_parameters=path_params,
                    query_parameters=query_params,
                    body_required='requestBody' in operation
                )
                operations.append(op)
    
    return operations

if __name__ == "__main__":
    generate_cli()
