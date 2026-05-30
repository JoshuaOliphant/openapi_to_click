"""Command-line entry point for the generator."""

from __future__ import annotations

from pathlib import Path

import click

from openapi_to_cli import __version__
from openapi_to_cli.client import (
    ClientGenerationError,
    discover_client_package,
    generate_python_client,
    initialize_package_directories,
    patch_pyproject,
)
from openapi_to_cli.render import build_context, default_template_dir, render_cli
from openapi_to_cli.spec import SpecError, load_spec


@click.command()
@click.version_option(__version__)
@click.argument("openapi_spec_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_path", type=click.Path(file_okay=False))
@click.option(
    "--template-path",
    type=click.Path(exists=True, file_okay=False),
    default=None,
    help="Directory containing cli_template.jinja2 (defaults to the bundled template).",
)
def generate_cli(
    openapi_spec_path: str, output_path: str, template_path: str | None
) -> None:
    """Generate a Click CLI from an OpenAPI specification.

    \b
    OPENAPI_SPEC_PATH  Path to the OpenAPI spec (YAML or JSON).
    OUTPUT_PATH        Directory where the generated client and cli.py are written.
    """
    try:
        spec = load_spec(openapi_spec_path)
    except SpecError as exc:
        raise click.ClickException(str(exc)) from exc

    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)

    try:
        generate_python_client(openapi_spec_path, output_path)
        client_package = discover_client_package(output_path)
    except ClientGenerationError as exc:
        raise click.ClickException(str(exc)) from exc

    initialize_package_directories(output_path, client_package)
    patch_pyproject(output_path)

    context = build_context(spec, client_package)
    template_dir = template_path or default_template_dir()
    cli_code = render_cli(template_dir, context)

    cli_file = output / "cli.py"
    cli_file.write_text(cli_code)

    click.echo(f"CLI generated at {cli_file}")


def main() -> None:
    """Console-script entry point."""
    generate_cli()


if __name__ == "__main__":
    main()
