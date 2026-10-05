# Project Progress

**Current phase:** Pre-release validation and documentation reconciliation

## Completed

- Confirmed workspace starts empty and is not a Git repository.
- Confirmed GitHub CLI is authenticated as `lukas-meszaros`; target repository lookup returned not found at initial inspection.
- Confirmed Python 3.9.6, Python 3.13.13, Docker, Git, and authenticated `gh`; the local Docker testbed runs two PostgreSQL 16.4 instances.
- Reviewed pg8000 1.31.5 DB-API documentation: DB-API 2.0, configurable named placeholder style, autocommit disabled by default, fetchmany support, and explicit TLS context support.
- Reviewed PostgreSQL transaction documentation: statements have implicit transaction boundaries when not enclosed in a transaction block; transaction group changes are atomic.
- Reviewed Python subprocess guidance: argv arrays, no shell, stdin/stdout/stderr pipes, timeout, and explicit child cleanup.
- Confirmed PyYAML SafeLoader supports standard tags only; unsafe object constructors must not be used.
- Defined preliminary design decisions in `PROJECT_PLAN.md`.
- Completed the initial runtime: safe YAML loading, strict validation/describe, CLI/config, trusted providers, pg8000 sessions, result modes, restricted resolver/conditions, transactions, output formats, and sequential execution.
- Added ten example templates, an isolated two-service PostgreSQL 16.4 testbed, and opt-in PostgreSQL integration tests.
- Live PostgreSQL checks verified parameter binding, cross-database session reuse, `new` isolation, reusable temporary-table state, transaction rollback, statement timeout classification/recovery, and end-to-end examples.
- Resolved two pg8000 DB-API integration details with live probes: call `execute(sql)` rather than `execute(sql, None)` for parameterless statements; do not fetch rows when `cursor.description is None`.
- Latest full live suite: 66 tests passed, including 5 PostgreSQL integration tests; the default non-integration suite has 61 passes and 5 explicit skips.
- Application configuration now exposes a global `session.mode` default; database and step settings override it.
- All ten example templates pass `dbeeapp validate` under the explicit testbed config and run in the integration example loop.
- A CPython 3.9 / manylinux2014 x86_64 binary-wheel resolution succeeded after pinning `scramp==1.4.6`; this is packaging compatibility evidence, not an RHEL runtime test.
- Built wheel and sdist; a no-index install of pinned runtime requirements and the built wheel ran `version` and `validate` from `/tmp`, proving the installed artifact and packaged provider path work on macOS arm64 / Python 3.13.13.
- Recorded one-run local timings for startup, small query, cross-database, 20 sequential steps, and 10,000 streamed rows in `docs/PERFORMANCE.md`; no RSS or statistical benchmark claims are made.

## Current

- Run final full tests, secret/artifact checks, and inspect every output/release artifact after the last small edits.
- Confirm exact CyberArk AIM endpoint and account selector against the supported deployment version.
- Test on the documented RHEL distribution/Python minor and finalize a support matrix.
- Verify no target GitHub repository exists immediately before any eventual creation; publish only once release gates are satisfied.

## Remaining

- Confirm CyberArk AIM endpoint/request protocol against the actual supported AIM version.
- Execute the built application on the target RHEL/Python minor and complete security/release review.
- Create and verify the public GitHub repository only after all release gates are satisfied.

## Test Status

- Full live suite: 66 passed, 0 failed; 5 live PostgreSQL integration cases passed.
- Two PostgreSQL 16.4 test containers are currently running locally; tests seed/reset only dummy local data.
- Python 3.13.13 is the only interpreter actually tested so far; Python 3.9.6 is installed on the host but not used for dependencies/tests.

## Known Limitations / Open Questions

- CyberArk provider is implemented but not certified against a real CyberArk AIM service; public documentation links tried were unavailable (HTTP 404), so endpoint path and account selector must be verified against an authoritative version-specific source or known-good target integration.
- PostgreSQL was tested using Docker image 16.4; RHEL and Python 3.9 are not yet tested.
- A network-disabled wheelhouse install succeeded on macOS; a matching RHEL runtime install has not been performed.
- GitHub repository was absent at the first lookup; repeat the check immediately before creation.
- Only single-run local timing observations exist; peak RSS and repeated-run distributions were not measured.
