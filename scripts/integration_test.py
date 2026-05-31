#!/usr/bin/env python
"""End-to-end integration test driven against a real running API.

This is the no-mock integration scenario: it starts the example FastAPI app on
a real port, generates a CLI from the app's *live* OpenAPI spec, then drives a
sequence of real CLI invocations over real HTTP and asserts on what they print
and the exit codes they return.

Because the spec is pulled from the running app, the handlers and the spec can
never drift apart — this doubles as a working, runnable example of the tool.

Run it directly::

    uv run python scripts/integration_test.py

It exits 0 on success and prints a transcript; any failed assertion exits 1.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
APP = "examples.petstore.app:app"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_spec(base_url: str, timeout: float = 30.0) -> dict:
    """Poll the app's /openapi.json until it answers (or time out)."""
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{base_url}/openapi.json", timeout=2.0)
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as exc:  # server not up yet
            last_exc = exc
        time.sleep(0.3)
    raise RuntimeError(f"App did not become ready at {base_url}: {last_exc}")


class _Runner:
    """Invokes the generated CLI and records pass/fail for each check."""

    def __init__(self, cli_path: Path, base_url: str) -> None:
        self.cli_path = cli_path
        self.base_url = base_url
        self.failures: list[str] = []

    def check(
        self,
        name: str,
        args: list[str],
        *,
        expect_exit: int = 0,
        expect_json: dict | None = None,
        expect_in: str | None = None,
    ) -> None:
        proc = subprocess.run(
            [sys.executable, str(self.cli_path), *args, "--base-url", self.base_url],
            capture_output=True,
            text=True,
            cwd=self.cli_path.parent,
        )
        out = proc.stdout.strip()
        # Error messages (click.ClickException) go to stderr, so match against both.
        combined = f"{proc.stdout}\n{proc.stderr}"
        problems = []
        if proc.returncode != expect_exit:
            problems.append(f"exit {proc.returncode} != {expect_exit}")
        if expect_json is not None:
            try:
                if json.loads(out) != expect_json:
                    problems.append(f"json {out!r} != {expect_json!r}")
            except json.JSONDecodeError:
                problems.append(f"output was not JSON: {out!r}")
        if expect_in is not None and expect_in not in combined:
            problems.append(f"{expect_in!r} not in output {combined!r}")

        status = "PASS" if not problems else "FAIL"
        print(f"  [{status}] {name}")
        if problems:
            for p in problems:
                print(f"         - {p}")
            if proc.stderr.strip():
                print(f"         stderr: {proc.stderr.strip()}")
            self.failures.append(name)


def main() -> int:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    print(f"Starting example app on {base_url} ...")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            APP,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=REPO_ROOT,
    )

    try:
        spec = _wait_for_spec(base_url)
        print(f"App ready: {spec['info']['title']} v{spec['info']['version']}")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec_file = tmp_path / "openapi.json"
            spec_file.write_text(json.dumps(spec))
            out_dir = tmp_path / "generated"

            print("Generating CLI from the live spec ...")
            gen = subprocess.run(
                [
                    "openapi-to-cli",
                    str(spec_file),
                    str(out_dir),
                ],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            if gen.returncode != 0:
                print(gen.stdout)
                print(gen.stderr)
                print("FAILED: generation did not succeed")
                return 1

            cli_path = out_dir / "cli.py"
            print(f"Driving generated CLI at {cli_path}\n")

            runner = _Runner(cli_path, base_url)

            # GET with a path parameter and an optional query parameter.
            runner.check(
                "GET get-pet with path + query params",
                ["get-pet", "--pet-id", "1", "--detail", "true"],
                expect_json={"id": 1, "name": "Rex", "tag": "dog"},
            )

            # POST with a JSON body deserialized into the generated model.
            runner.check(
                "POST create-pet with --body",
                ["create-pet", "--body", '{"name": "Mittens", "tag": "cat"}'],
                expect_in='"name": "Mittens"',
            )

            # Authenticated request: --token must reach the server as a bearer.
            runner.check(
                "GET whoami with --token (AuthenticatedClient)",
                ["whoami", "--token", "s3cr3t"],
                expect_json={"token": "s3cr3t"},
            )

            # Error status: a 404 must surface as a non-zero exit.
            runner.check(
                "GET get-pet missing id exits non-zero on 404",
                ["get-pet", "--pet-id", "999"],
                expect_exit=1,
            )

            # Malformed --body must be a clean error, not a traceback.
            runner.check(
                "POST create-pet with invalid JSON body",
                ["create-pet", "--body", "{not json}"],
                expect_exit=1,
                expect_in="not valid JSON",
            )

            print()
            if runner.failures:
                print(
                    f"INTEGRATION TEST FAILED: {len(runner.failures)} check(s) failed"
                )
                return 1
            print("INTEGRATION TEST PASSED: all checks green")
            return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
