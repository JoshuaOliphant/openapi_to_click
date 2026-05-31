# Testing guide

This document is the institutional memory for testing this generator. It exists
because the generator's output is *code*, and "the spec parsed fine" says nothing
about whether the generated CLI compiles, imports, or actually runs. Read this
before changing `naming.py`, `render.py`, or the Jinja template.

## The three layers, and what each is for

| Layer | File | Catches |
| ----- | ---- | ------- |
| Spec loading | `tests/test_spec.py` | validation, file formats, base-URL selection |
| Rendering | `tests/test_render.py` | the **real** template renders, `compile()`s, and produces correct imports/params/commands |
| End-to-end generation | `tests/test_generate.py` | the full opc subprocess pipeline; generated `cli.py` compiles with tag-aware imports |
| Live integration | `scripts/integration_test.py` | a generated CLI **actually runs** against a real server (params, `--body`, `--token`, error exit) |

The golden rule: **a spec that "generates without error" is not a passing test.**
The generated file can still fail to compile, fail to import the client, or omit
a required argument so the command is uncallable. Always push the output through
`compile()` at minimum, and ideally import it and/or run it.

## The core invariant: names MUST match openapi-python-client

The single richest source of bugs is **name drift**. The generated `cli.py`
imports from, and calls into, the client that opc produced. If our derived
module path, function name, or keyword argument differs from what opc actually
emitted — even by one character — the generated CLI is broken (ImportError,
SyntaxError, or TypeError at call time).

Therefore `naming.py` delegates to opc's own `PythonIdentifier`, `snake_case`,
`pascal_case`, and `kebab_case`. Do **not** hand-roll these. Key facts learned
the hard way:

- opc names endpoint module files `PythonIdentifier(endpoint.name, "field_")`.
  This snake-cases **and** escapes Python reserved words (`import` → `import_`)
  and prefixes leading-digit names (`2fa` → `field_2fa`). Bare `snake_case` does
  *not* do the escaping and will emit invalid imports.
- Parameter kwargs use the same `PythonIdentifier(name, "field_")` rule
  (`class` → `class_`, `2fa` → `field_2fa`).
- Tag directories use prefix `"tag"` (no underscore): `2fa` → `tag2fa`.
- opc collapses operations that resolve to the **same module** into one client
  function (last definition wins). So duplicate/colliding operationIds must
  produce exactly one command, not shadowed duplicate `def`s.

When in doubt about what opc emits, **generate a client and look** — don't guess:

```bash
uv run openapi-to-cli /tmp/some_spec.json /tmp/out
ls /tmp/out/*/api/*/                       # actual module file names
grep -A8 'def _get_kwargs' /tmp/out/*/api/*/<module>.py   # actual kwarg names
```

## The torture-spec checklist

When touching generation logic, run a spec through the full pipeline for **each**
of these and confirm it (a) generates, (b) `compile()`s, (c) `--help` works, and
where relevant (d) the command is actually callable. These each correspond to a
bug that has been found and fixed at least once:

1. **Reserved-word operationId / param** (`import`, `class`, `from`) — must be
   escaped to `import_`, `class_`, etc. (else SyntaxError).
2. **Leading-digit names** (`2fa`) — param → `field_2fa`, tag → `tag2fa`.
3. **Duplicate operationIds that normalise to one module** (`list_items` vs
   `list-items`) — exactly one command, no shadowed def.
4. **Same operationId under different tags** (`list` in `pets` and `owners`) —
   distinct func names, import aliases, and command names; both reachable.
5. **`$ref` parameters** (`{"$ref": "#/components/parameters/IdParam"}`) — must be
   resolved against `components`, not dropped (else the required arg is missing
   and the call raises TypeError).
6. **Path-level (shared) parameters** — declared once under the path, applied to
   every method; must be merged into each command.
7. **No `operationId`** — fall back to a name derived from method + path.
8. **No `servers`** — `--base-url` becomes required (no default).
9. **Multiple servers, first relative** — default base-url is the first
   *absolute* URL, skipping relative ones like `/api`.
10. **Tags with spaces / punctuation / unicode** (`Pet Store!`, `café münü`) —
    sanitised to match opc's tag directory names.
11. **Inline (non-`$ref`) request body** — accepted as `--body` JSON, passed as a
    dict (not coerced to a model).
12. **`allOf` / `oneOf` request body** — generates and compiles (body handled
    generically).
13. **`enum` / `array` parameters** — generate valid options.
14. **Empty `paths`** — produces a valid CLI with zero commands.

A quick way to run the battery is to drop specs in a temp dir and loop:

```bash
for s in /tmp/specs/*.json; do
  d=/tmp/out/$(basename "$s" .json)
  uv run openapi-to-cli "$s" "$d" >/dev/null 2>&1 \
    && uv run python -c "import py_compile; py_compile.compile('$d/cli.py', doraise=True)" \
    && (cd "$d" && uv run python cli.py --help >/dev/null 2>&1) \
    && echo "OK  $(basename "$s")" || echo "FAIL $(basename "$s")"
done
```

## Generated-CLI runtime behavior to verify

The live integration test (`scripts/integration_test.py`) drives a generated CLI
against the example FastAPI app. When changing the template, re-check these by
hand too — they are common user paths and each has regressed before:

- GET with path + query params prints the parsed JSON body.
- POST with `--body '<json>'` and `--body @file.json`.
- `--token` reaches the server (requires the spec to declare an HTTP **security
  scheme** — a plain header param will NOT be wired to `AuthenticatedClient`).
- `--output raw` prints the raw bytes; default prints pretty JSON.
- **Failure UX must be clean, not tracebacks**: unreachable server, malformed
  `--body` JSON, and an unreadable `@file` should all print `Error: ...` and exit
  non-zero (handled via `click.ClickException` in the template).

## Before opening or updating a PR

Run all gates and the live integration scenario, and report the result:

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest tests
uv run python scripts/integration_test.py
```
