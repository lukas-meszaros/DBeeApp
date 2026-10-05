# Testing

## Levels

- Unit tests: loader safety, duplicate keys, schema/unknown-key validation, reference resolver, conditions, path traversal, provider protocol, secret redaction, result limits, session registry, transaction rollback, output formatting, exit categories.
- CLI tests: validate/describe do not invoke providers, connect, execute SQL, or create output; run behavior and diagnostics are stable.
- PostgreSQL integration tests: run only when both testbed services are available; verify SQL binding, cross-database reuse, isolated new sessions, overrides, temporary state, DML commit, transaction rollback, connection cleanup, stream limits, server NOTICE forwarding, procedure reference execution, and outputs.
- Server-output unit tests cover notice severity/message routing, detail/hint exclusion, truncation, bounded-buffer overflow, and optional file output.
- Security tests: malicious YAML tags, arbitrary provider paths, malformed/oversized provider output, timeout, stdout/stderr/log/exception secret scans, traversal/symlink paths, unknown references and IDs.

## Testbed

`testbed/compose.yaml` runs two independent PostgreSQL services (`db_control` and `db_reporting`) with test-only credentials, explicit health checks, initialization SQL, and deterministic seed rows. It must not use production credentials. Integration tests must clearly skip when Docker/services are unavailable rather than imply they ran.

Initialization seeds 300 application rows in each database and 10,000 reporting rows. The external-SQL CSV example selects 300 rows; the large-result example streams 10,000.

## Commands

```sh
python3 -S -m unittest discover -s tests -v
docker compose -f testbed/compose.yaml up -d
DBEEAPP_INTEGRATION=1 python3 -S -m unittest discover -s tests -v
docker compose -f testbed/compose.yaml down
```

No `down -v` command should be required for normal runs; volumes are local disposable test state and must not contain user data.

## Session Assertions

Use `SELECT pg_backend_pid()` to prove reuse, switching, new connections, per-step override identities, and identical transaction-child session identity. Verify `pg_temp` table visibility for reuse and absence for a new session. Stream a large parameterized SELECT through a server-side cursor into JSONL/CSV and check row count and bounded output. `examples/many_sequential_steps/job.yaml` provides a 20-query reusable-session workload for timing checks. Force a SQL error inside a transaction and verify prior DML is rolled back and later child SQL is not invoked. Instrument fake connections for closure on all failure paths. Runtime imports must also pass under `python -S` so installed `site-packages` cannot mask missing vendored modules.

## Release Evidence

Record Python, PostgreSQL, pg8000, dependency, and test counts/results in `PROGRESS.md` and release notes. Never report a test as passed if it was skipped or not run.
