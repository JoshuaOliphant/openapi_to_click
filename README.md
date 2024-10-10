# OpenAPI Click CLI Generator

## Overview
The **OpenAPI Click CLI Generator** is a Python application that automatically generates a command-line interface (CLI) from an OpenAPI specification. The generated CLI allows easy interaction with the API defined in the OpenAPI spec, leveraging Python's Click library.

## Features
- Generates Python clients from an OpenAPI spec using **openapi-python-client**.
- Uses **Click** to provide an intuitive CLI for interacting with the generated API.
- Supports YAML and JSON OpenAPI spec formats.
- Customizable templates using **Jinja2**.

## Prerequisites
Ensure you have the following dependencies installed:

- Python 3.12+
- Click
- Jinja2
- openapi-python-client
- PyYAML
- Pydantic
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

You can install the required dependencies using and create the virtual environment with:
```sh
uv sync
source .venv/bin/activate
```

### Running the Project
After activating the virtual environment, you can run the project with the `--help` flag to see the available options:
```sh
uv run python main.py --help
Usage: main.py [OPTIONS] OPENAPI_SPEC_PATH OUTPUT_PATH

  Generate a command-line interface (CLI) for an OpenAPI specification.

  Arguments: - OPENAPI_SPEC_PATH: Path to the OpenAPI specification file
  (YAML/JSON). - OUTPUT_PATH: Directory where the generated CLI will be saved.
  - TEMPLATE_PATH: Path to the directory containing the Jinja templates
  (optional).

Options:
  --template-path PATH  Path to the directory containing the Jinja templates.
  --help                Show this message and exit.
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
python main.py openapi_spec.yaml ./output
```
This command will generate a CLI from the `openapi_spec.yaml` file and save it in the `./output` directory.

### Generated CLI
After generating the CLI, you can run the following command to see the available options:
```sh
python output/cli.py --help
```

## Customization
The CLI generator uses Jinja2 templates to create the command-line interface. If needed, you can modify the `cli_template.jinja2` to change the structure of the generated CLI.

### Building Distributions
To build a source or binary distribution (wheel) for your project, use:
```sh
uv build
```

## License
This project is licensed under the MIT License.

## Contributing
Contributions are welcome! Feel free to open an issue or submit a pull request if you have any suggestions or improvements.
