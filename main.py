import os
import click
import yaml
import json
import logging
from typing import List, Optional, Any, Dict
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, ValidationError, field_validator, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TypeSchema(BaseModel):
    """Represents an OpenAPI type schema."""
    type: str = Field(..., description="The type of the parameter")
    format: Optional[str] = Field(None, description="The format of the parameter")
    default: Any = Field(None, description="Default value")
    enum: Optional[List[Any]] = Field(None, description="Possible enum values")

    @field_validator('type')
    def validate_schema_type(cls, v):
        valid_types = {'string', 'number', 'integer', 'boolean', 'array', 'object', 'null'}
        if v not in valid_types:
            raise ValueError(f"Schema type must be one of {valid_types}")
        return v

    @field_validator('format')
    def validate_format(cls, v, values):
        if v is not None:
            type_formats = {
                'string': {'date', 'date-time', 'password', 'byte', 'binary', 'email', 'uuid', 'uri', 'hostname'},
                'integer': {'int32', 'int64'},
                'number': {'float', 'double'}
            }
            schema_type = values.data.get('type')
            if schema_type in type_formats and v not in type_formats[schema_type]:
                raise ValueError(f"Invalid format '{v}' for type '{schema_type}'")
        return v

    class Config:
        extra = "allow"

class Parameter(BaseModel):
    """Represents an API endpoint parameter."""
    name: str = Field(..., description="Parameter name")
    description: str = Field("", description="Parameter description")
    required: bool = Field(default=False, description="Whether the parameter is required")
    type: str = Field(..., description="Parameter type")
    default: Any = Field(default=None, description="Default value for the parameter")
    in_: str = Field(..., alias="in", description="Parameter location (path, query, header, cookie)")
    schema_: Optional[TypeSchema] = Field(None, alias="schema", description="Parameter schema")
    example: Optional[Any] = Field(None, description="Example value")

    @field_validator('type')
    def validate_type(cls, v):
        valid_types = {'string', 'number', 'integer', 'boolean', 'array', 'object'}
        if v not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}")
        return v

    @field_validator('in_')
    def validate_parameter_in(cls, v):
        valid_locations = {'path', 'query', 'header', 'cookie'}
        if v not in valid_locations:
            raise ValueError(f"Parameter location must be one of {valid_locations}")
        return v

    class Config:
        frozen = True
        populate_by_name = True  # Allow both alias and Python names

class OperationResponse(BaseModel):
    """Represents an API operation response."""
    status_code: str = Field(..., description="HTTP status code")
    description: str = Field("", description="Response description")
    content_type: Optional[str] = Field(None, description="Response content type")
    schema_: Optional[TypeSchema] = Field(None, alias="schema", description="Response schema")

    @field_validator('status_code')
    def validate_status_code(cls, v):
        try:
            code = int(v)
            if not (100 <= code <= 599):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Status code must be a valid HTTP status code (100-599)")
        return v

    class Config:
        frozen = True
        populate_by_name = True

class Operation(BaseModel):
    """Represents an API operation/endpoint."""
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Endpoint path")
    tag: List[str] = Field(default_factory=list, description="Operation tags")
    summary: str = Field(default="", description="Operation summary")
    description: str = Field(default="", description="Detailed description")
    snake_case_name: str = Field(..., description="Python-friendly operation name")
    path_parameters: List[Parameter] = Field(default_factory=list, description="Path parameters")
    query_parameters: List[Parameter] = Field(default_factory=list, description="Query parameters")
    body_required: bool = Field(default=False, description="Whether request body is required")
    responses: Dict[str, OperationResponse] = Field(
        default_factory=dict,
        description="Operation responses"
    )
    deprecated: bool = Field(default=False, description="Whether the operation is deprecated")
    body_schema: Optional[TypeSchema] = Field(None, description="Schema for request body")

    @field_validator('method')
    def validate_method(cls, v):
        valid_methods = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options'}
        if v.lower() not in valid_methods:
            raise ValueError(f"Method must be one of {valid_methods}")
        return v.lower()

    def get_successful_response(self) -> Optional[OperationResponse]:
        """Get the successful response (2xx) if it exists."""
        for status_code, response in self.responses.items():
            if status_code.startswith('2'):
                return response
        return None

    def has_json_response(self) -> bool:
        """Check if the operation has a JSON response."""
        success_response = self.get_successful_response()
        if success_response and success_response.content_type:
            return 'application/json' in success_response.content_type
        return False

    def get_required_parameters(self) -> List[Parameter]:
        """Get all required parameters for this operation."""
        return [p for p in self.path_parameters + self.query_parameters if p.required]

    class Config:
        frozen = True

class OpenAPISpec(BaseModel):
    openapi: str = Field(..., description="OpenAPI specification version")
    info: dict = Field(..., description="API information")
    paths: dict = Field(..., description="API paths and operations")
    operations: List[Operation] = Field(default_factory=list, description="Extracted operations")

    class Config:
        extra = "allow"  # Allow additional fields that might be in the OpenAPI spec

    def get_operations_by_tag(self, tag: str) -> List[Operation]:
        """Get all operations for a specific tag."""
        return [op for op in self.operations if tag in op.tag]

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
                    schema = param.get('schema', {})
                    type_schema = TypeSchema(
                        type=schema.get('type', 'string'),
                        format=schema.get('format'),
                        default=schema.get('default'),
                        enum=schema.get('enum')
                    )

                    param_obj = Parameter(
                        name=param['name'],
                        description=param.get('description', ''),
                        required=param.get('required', False),
                        type=type_schema.type,
                        default=type_schema.default,
                        in_=param['in'],
                        schema_=type_schema,
                        example=param.get('example')
                    )

                    if param['in'] == 'path':
                        path_params.append(param_obj)
                    elif param['in'] == 'query':
                        query_params.append(param_obj)

                # Extract responses
                responses = {}
                for status_code, response_data in operation.get('responses', {}).items():
                    content_type = next(iter(response_data.get('content', {})), None)
                    schema = None
                    if content_type:
                        schema_data = response_data['content'][content_type].get('schema', {})
                        schema = TypeSchema(**schema_data)

                    responses[status_code] = OperationResponse(
                        status_code=status_code,
                        description=response_data.get('description', ''),
                        content_type=content_type,
                        schema_=schema
                    )

                # Extract request body information
                request_body = operation.get('requestBody', {})
                body_required = request_body.get('required', False)
                body_content = request_body.get('content', {})
                body_schema = None
                if 'application/json' in body_content:
                    body_schema = TypeSchema(**body_content['application/json'].get('schema', {}))

                # Create operation object
                op = Operation(
                    method=method,
                    path=path,
                    tag=operation.get('tags', ['default']),
                    summary=operation.get('summary', ''),
                    description=operation.get('description', ''),
                    snake_case_name=snake_case(path.strip('/').replace('/', '_')),
                    path_parameters=path_params,
                    query_parameters=query_params,
                    body_required=body_required,
                    body_schema=body_schema,
                    responses=responses,
                    deprecated=operation.get('deprecated', False)
                )
                operations.append(op)

    return operations

if __name__ == "__main__":
    generate_cli()
