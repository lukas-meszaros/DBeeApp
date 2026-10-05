# Project Progress

**Current phase:** Pre-release validation and documentation reconciliation

## Completed

- Confirmed workspace starts empty and is not a Git repository.
- Confirmed GitHub CLI is authenticated as `lukas-meszaros`; target repository was absent before creation.
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
- Created and verified public `https://github.com/lukas-meszaros/DBeeApp` on `main`. No release tag was created.
- Final high-confidence secret scan found no GitHub/AWS token patterns or private-key material; committed credential-like values are explicitly dummy testbed values.

## Current

- Keep the public source snapshot current; a certified release remains blocked on target-environment checks below.

## Remaining

- Confirm CyberArk AIM endpoint/request protocol against the actual supported AIM version.
- Execute the built application on the target RHEL/Python minor.
- Validate CyberArk AIM against an authoritative supported service version.
- Complete repeated performance/RSS measurements and final release review before tagging a certified release.

## Test Status

- Full live suite: 66 passed, 0 failed; 5 live PostgreSQL integration cases passed.
- Two PostgreSQL 16.4 test containers are currently running locally; tests seed/reset only dummy local data.
- Python 3.13.13 is the only interpreter actually tested so far; Python 3.9.6 is installed on the host but not used for dependencies/tests.

## Known Limitations / Open Questions

- CyberArk provider is implemented but not certified against a real CyberArk AIM service; public documentation links tried were unavailable (HTTP 404), so endpoint path and account selector must be verified against an authoritative version-specific source or known-good target integration.
- PostgreSQL was tested using Docker image 16.4; RHEL and Python 3.9 are not yet tested.
- A network-disabled wheelhouse install succeeded on macOS; a matching RHEL runtime install has not been performed.
- High-confidence source scan found no token/private-key patterns; a broader organization-specific secret scanner was not available.
- Repository is public, but no certified release/tag exists yet.
- Only single-run local timing observations exist; peak RSS and repeated-run distributions were not measured.
