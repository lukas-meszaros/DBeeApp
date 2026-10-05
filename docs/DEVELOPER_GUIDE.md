# Developer Guide

## Before Changing Code

Read `CLAUDE.md`, `FILE_INDEX.md`, `ARCHITECTURE.md`, `TEMPLATE_SPEC_V1.md`, and `PROGRESS.md`. Keep changes small and update the spec/docs before changing public workflow behavior.

## Environment

Runtime libraries are already included under `dbeeapp/_vendor`; do not install `requirements-runtime.txt` or any runtime package. Run DBeeApp and tests directly with Python; `-S` disables site initialization and verifies the vendor tree is sufficient. `requirements-dev.txt` is a pin/reference list for optional build front ends, not needed to run the application or tests.

```sh
python3 -S -m unittest discover -s tests -v
python3 -S -m dbeeapp version
```

## Code Boundaries

- CLI owns argument parsing, command routing, and process exit behavior.
- Loader owns safe YAML input and source location handling.
- Validator owns schema, references, and path/combination checks before side effects.
- Resolver and conditions own restricted template values and declarative conditions.
- Credential runner owns provider name resolution, process protocol, output limits, and timeout/cleanup.
- Session manager owns connection creation/reuse/new semantics and closure; database adapter owns pg8000-specific execution and error classification.
- Engine owns sequential ordering, step state, and error policy.
- Transaction module owns atomic group boundaries on one connection.
- Result/output modules own bounded result representation and serialization.

Avoid circular imports. Provider scripts intentionally do not import DBeeApp internals.

## Tests

Use Python `unittest` to keep test dependencies minimal. Unit tests should use fakes for database/provider processes where possible. Integration tests use the independent `db_control` and `db_reporting` services from `testbed/compose.yaml` and must verify PostgreSQL backend PIDs for session guarantees. Security tests assert secrets are absent from every user-visible channel.

Run all unit tests and applicable integration tests. Report skipped integration tests as skipped, not passed. Test a behavior at its narrowest scope immediately after changing it, then run the broader suite before release.

## Dependency and Release Changes

Update exact pins and the vendor tree together. On a connected maintenance workstation, use `pip download` to fill a local wheelhouse, then run `tools/vendor_runtime.py`; this downloads archives but does not install runtime libraries. Verify the source/versions/licenses and add a `python -S` test. Do not add a runtime dependency without explaining why the standard library or current dependencies are insufficient. Never commit unneeded wheelhouse archives, local venvs, database volumes, logs, or credentials.
