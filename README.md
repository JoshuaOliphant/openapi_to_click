# OpenAPI Click CLI Generator

## Overview
The **OpenAPI Click CLI Generator** is a Python application that automatically generates a command-line interface (CLI) from an OpenAPI specification. The generated CLI allows easy interaction with the API defined in the OpenAPI spec, leveraging Python's Click library.

## Features
- Generates a standalone CLI directly from OpenAPI specifications
- Uses **Click** to provide an intuitive CLI for interacting with APIs
- Supports YAML and JSON OpenAPI spec formats
- Handles path parameters, query parameters, and request bodies
- Customizable templates using **Jinja2**
- No external API client dependencies required (uses Python requests library)
- Clean and consistent command naming
- Proper type hints and validation
- Automatic help message generation

## Prerequisites
Ensure you have the following dependencies installed:

- Python 3.12+
- Click
- Jinja2
- PyYAML
- Pydantic
- Requests

You can install the required dependencies using:
```sh
pip install click jinja2 pyyaml pydantic requests
```

Or using the project's dependency management:
```sh
pip install -e .
```

## Usage
The CLI generator script takes in an OpenAPI specification and outputs a CLI for interacting with the specified API.

### Command
```sh
python main.py <OPENAPI_SPEC_PATH> <OUTPUT_PATH> [--template-path TEMPLATE_PATH]
```

- **OPENAPI_SPEC_PATH**: Path to the OpenAPI specification file (YAML/JSON).
- **OUTPUT_PATH**: Directory where the generated CLI will be saved.
- **TEMPLATE_PATH**: (Optional) Path to the directory containing the Jinja templates.

### Example
```sh
# Generate a CLI from an OpenAPI spec
python main.py openapi_spec.yaml ./output

# Use the generated CLI
python output/cli.py --help
```

### Generated CLI Features
- Clean, consistent command naming (e.g., `get-users`, `create-post`)
- Full parameter support:
  - Path parameters (e.g., `/users/{id}` → `--id`)
  - Query parameters (e.g., `?page=1&limit=10` → `--page 1 --limit 10`)
  - Request bodies (passed as JSON strings)
- Proper type hints and validation
- Helpful error messages
- Automatic help documentation generation
- Direct HTTP requests using Python's requests library
- JSON request/response handling

### Example Usage
For an API endpoint like `POST /posts` that creates a blog post:
```sh
python cli.py post-posts \
  --base-url https://api.example.com/v1 \
  --data '{"title": "Hello World", "content": "My first post!", "author": "John"}'
```

For an endpoint with path and query parameters like `GET /posts/{id}/comments?page=1`:
```sh
python cli.py get-posts-comments \
  --base-url https://api.example.com/v1 \
  --post-id 123 \
  --page 1
```

## Generated CLI Structure
The generator creates a standalone Python script that:
1. Uses Click for command-line argument parsing
2. Handles parameter validation and type conversion
3. Makes HTTP requests using the requests library
4. Processes JSON request/response bodies
5. Provides helpful error messages and documentation

## Customization
The CLI generator uses Jinja2 templates to create the command-line interface. You can customize:
1. Command naming format
2. Parameter handling
3. HTTP client behavior
4. Error handling
5. Output formatting

Modify the `cli_template.jinja2` template to change the structure of the generated CLI.

## License
This project is licensed under the MIT License.

## Contributing
Contributions are welcome! Feel free to open an issue or submit a pull request if you have any suggestions or improvements. Some areas for potential improvement:

1. Better error handling and user feedback
2. Support for authentication methods
3. Custom response formatting options
4. Interactive mode for complex operations
5. Support for file uploads
6. OpenAPI validation improvements
