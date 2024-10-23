import yaml
from main import extract_operations, OpenAPISpec

def test_parser():
    # Load the test API spec
    with open('/tmp/test_api.yaml', 'r') as f:
        spec_data = yaml.safe_load(f)

    # Validate the spec
    spec = OpenAPISpec(**spec_data)

    # Extract operations
    operations = extract_operations(spec_data)

    print("=== Testing OpenAPI Parser ===\n")

    # Test operations parsing
    print(f"Found {len(operations)} operations:")
    for op in operations:
        print(f"\nOperation: {op.method.upper()} {op.path}")
        print(f"Tags: {op.tag}")
        print(f"Summary: {op.summary}")

        # Test parameter handling
        if op.path_parameters:
            print("\nPath Parameters:")
            for param in op.path_parameters:
                print(f"  - {param.name} ({param.type})")
                if param.schema_:
                    print(f"    Format: {param.schema_.format}")

        if op.query_parameters:
            print("\nQuery Parameters:")
            for param in op.query_parameters:
                print(f"  - {param.name} ({param.type})")
                if param.schema_ and param.schema_.enum:
                    print(f"    Enum values: {param.schema_.enum}")

        # Test response handling
        print("\nResponses:")
        for status_code, response in op.responses.items():
            print(f"  - {status_code}: {response.description}")
            if response.schema_:
                print(f"    Content Type: {response.content_type}")

        # Test convenience methods
        success_response = op.get_successful_response()
        if success_response:
            print(f"\nSuccessful Response: {success_response.status_code}")

        if op.has_json_response():
            print("Has JSON Response: Yes")

        required_params = op.get_required_parameters()
        if required_params:
            print("\nRequired Parameters:")
            for param in required_params:
                print(f"  - {param.name}")

        if op.body_schema:
            print("\nRequest Body Schema:")
            print(f"  Type: {