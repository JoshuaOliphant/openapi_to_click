"""Driving openapi-python-client and preparing its output tree."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import tomlkit


class ClientGenerationError(Exception):
    """Raised when the underlying client generation fails."""


def generate_python_client(spec_path: str | Path, output_path: str | Path) -> None:
    """Generate a Python API client into ``output_path`` using opc.

    Raises:
        ClientGenerationError: if opc is unavailable or exits non-zero.
    """
    executable = shutil.which("openapi-python-client")
    if executable is None:
        raise ClientGenerationError(
            "openapi-python-client is not on PATH. Run inside `uv run` or an "
            "activated virtualenv where the project dependencies are installed."
        )

    try:
        subprocess.run(
            [
                executable,
                "generate",
                "--path",
                str(spec_path),
                "--output-path",
                str(output_path),
                "--overwrite",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ClientGenerationError(
            f"openapi-python-client failed with exit code {exc.returncode}."
        ) from exc


def discover_client_package(output_path: str | Path) -> str:
    """Return the name of the generated client package.

    Identified reliably by the ``client.py`` module openapi-python-client always
    emits, rather than guessing at "the first directory".
    """
    output = Path(output_path)
    candidates = sorted(
        child.name
        for child in output.iterdir()
        if child.is_dir() and (child / "client.py").is_file()
    )
    if not candidates:
        raise ClientGenerationError(
            f"Could not locate a generated client package under {output}."
        )
    return candidates[0]


def initialize_package_directories(
    output_path: str | Path, client_package: str
) -> None:
    """Ensure the output dir and client package are importable packages."""
    output = Path(output_path)
    for directory in (output, output / client_package):
        init_file = directory / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# This file makes this directory a package.\n")


def patch_pyproject(output_path: str | Path) -> None:
    """Add ``click`` to the generated client's dependencies.

    The generated CLI imports Click, so the standalone project needs it declared.
    Handles both the Poetry-style table that openapi-python-client emits by
    default and the PEP 621 ``[project]`` array (used with ``--meta pdm``).
    Editing is done with ``tomlkit`` to preserve the existing formatting.
    """
    pyproject = Path(output_path) / "pyproject.toml"
    if not pyproject.exists():
        return

    doc = tomlkit.parse(pyproject.read_text())

    poetry_deps = doc.get("tool", {}).get("poetry", {}).get("dependencies")
    if poetry_deps is not None:
        if "click" not in poetry_deps:
            poetry_deps["click"] = "^8.1.7"
        pyproject.write_text(tomlkit.dumps(doc))
        return

    project = doc.get("project")
    if project is not None:
        deps = project.get("dependencies")
        if deps is None:
            deps = tomlkit.array()
            project["dependencies"] = deps
        if not any(str(dep).lower().startswith("click") for dep in deps):
            deps.append("click>=8.1.7")
        pyproject.write_text(tomlkit.dumps(doc))
