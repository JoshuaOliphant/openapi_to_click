"""End-to-end tests: run the full pipeline including openapi-python-client."""

from pathlib import Path

from click.testing import CliRunner

from openapi_to_cli.cli import generate_cli


def _generate(spec_path, output_dir, extra=None):
    return CliRunner().invoke(
        generate_cli, [spec_path, str(output_dir), *(extra or [])]
    )


def test_generates_compilable_cli_from_json(write_spec, valid_openapi_spec, tmp_path):
    spec_path = write_spec(valid_openapi_spec, "json")
    output_dir = tmp_path / "out"

    result = _generate(spec_path, output_dir)

    assert result.exit_code == 0, result.output
    cli_py = output_dir / "cli.py"
    assert cli_py.exists()
    # The bundled template is used by default (no --template-path needed).
    source = cli_py.read_text()
    compile(source, str(cli_py), "exec")
    assert "api.items.read_item" in source
    assert "api.widgets.create_widget" in source


def test_generates_from_yaml(write_spec, valid_openapi_spec, tmp_path):
    result = _generate(write_spec(valid_openapi_spec, "yaml"), tmp_path / "out")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "cli.py").exists()


def test_creates_nested_output_directory(write_spec, valid_openapi_spec, tmp_path):
    output_dir = tmp_path / "nested" / "out"
    result = _generate(write_spec(valid_openapi_spec), output_dir)
    assert result.exit_code == 0, result.output
    assert (output_dir / "cli.py").exists()


def test_patches_generated_pyproject_with_click(
    write_spec, valid_openapi_spec, tmp_path
):
    output_dir = tmp_path / "out"
    _generate(write_spec(valid_openapi_spec), output_dir)
    pyproject = (output_dir / "pyproject.toml").read_text()
    assert "click" in pyproject


def test_missing_spec_file_errors(tmp_path):
    result = _generate("nonexistent.yaml", tmp_path / "out")
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_unsupported_format_errors(tmp_path):
    bad = tmp_path / "spec.txt"
    bad.write_text("nope")
    result = _generate(str(bad), tmp_path / "out")
    assert result.exit_code == 1
    assert "Unsupported file format" in result.output


def test_respects_explicit_template_path(write_spec, valid_openapi_spec, tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "cli_template.jinja2").write_text("# custom {{ api_title }}\n")
    output_dir = tmp_path / "out"

    result = _generate(
        write_spec(valid_openapi_spec),
        output_dir,
        ["--template-path", str(template_dir)],
    )

    assert result.exit_code == 0, result.output
    assert Path(output_dir / "cli.py").read_text() == "# custom Test API\n"
