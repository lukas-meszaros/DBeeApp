# Developer Guide

## Before Changing Code

Read `CLAUDE.md`, `FILE_INDEX.md`, `ARCHITECTURE.md`, `TEMPLATE_SPEC_V1.md`, and `PROGRESS.md`. Keep changes small and update the spec/docs before changing public workflow behavior.

## Environment

The supported Python floor is to be confirmed against the pinned dependency set and target RHEL release. Use an isolated venv and install development dependencies from a connected staging environment. Production installs use only the runtime lock and wheelhouse.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
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

Update exact pins and full transitive lock together. Regenerate artifacts on a compatible target platform, compute and verify SHA-256 hashes, and test installation with `--no-index`. Do not add a runtime dependency without explaining why the standard library or current dependencies are insufficient. Never commit secrets, generated wheelhouse, local venvs, database volumes, logs, or credentials.
