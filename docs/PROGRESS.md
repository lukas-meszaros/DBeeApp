# Project Progress

**Current phase:** Local dependency and job-layout transition implemented; certification work remains

## Completed

- Implemented the CLI, strict YAML validation/describe, trusted providers, session registry, sequential engine, transaction groups, conditions, result modes, and outputs.
- Runtime third-party libraries are checked in as pure-Python source under `dbeeapp/_vendor`; `dbeeapp/__init__.py` loads them locally before runtime imports.
- Verified the runtime with Python 3.9.6 and `python -S`, which disables site initialization. The CLI and all runtime imports work without installed third-party packages.
- Verified all six vendored distributions have license text and `.dist-info` metadata; the vendor tree contains no native extension files.
- Moved all eleven examples to `examples/<job>/job.yaml`, each with a sibling `sql/` directory. `external_sql` keeps its query under `examples/external_sql/sql/`.
- All eleven job templates pass CLI validation under Python 3.9.6 with `-S`.
- Provider defaults can be configured centrally in application YAML, with per-database `credential.options` taking precedence. `dbeeapp.yaml.example` is an inert production-oriented template; `dbeeapp.testbed.yaml` is explicitly local-only.
- PostgreSQL server NOTICE/INFO messages can be routed (opt-in) to stdout and/or a separate append-only file; the buffer and message sizes are bounded, and only severity/message fields are forwarded.
- Added `examples/procedure_reference`, demonstrating dynamic session variables, preflight checks, procedure creation/call, post-call query, and `RAISE NOTICE`; added 300 application fixtures in each database and a data-backed CSV example.
- All five live PostgreSQL integration tests pass under Python 3.9.6 with `-S` against two PostgreSQL 16.4 containers. Procedure NOTICE forwarding and the 300-row CSV output are asserted end to end.
- Latest full suite: 85 tests passed, 0 failed under Python 3.9.6 with `-S`, including five live PostgreSQL integration tests.
- `compileall`, editor diagnostics, and a high-confidence token/private-key pattern scan passed.
- Public repository `https://github.com/lukas-meszaros/DBeeApp` is on `main`. No certified release tag exists.

## Test Status

- Python 3.9.6, site disabled: final full run passed 85 tests, including five live PostgreSQL integration tests.
- PostgreSQL 16.4: both testbed services passed reuse/new/override/temp-state, transaction identity/rollback, timeout recovery, and example workflow tests.
- Local test containers are stopped after integration validation; named volumes are preserved.
- Python 3.13.13 also passed earlier validation before the vendoring transition; latest full suite was run on Python 3.9.6.

## Remaining

- Verify CyberArk AIM endpoint/request semantics against the supported service release.
- Execute on the target RHEL distribution and document its exact Python support matrix.
- Complete repeated performance and peak-memory measurements before making deployment claims.
- Perform final release review before creating a certified release tag.

## Known Limitations

- CyberArk provider code is not certified against a real AIM service; public documentation links tried returned HTTP 404.
- RHEL itself has not been exercised, though the vendored pure-Python runtime was tested on Python 3.9.6.
- Performance results are single-run local macOS/Docker observations; peak RSS and repeated-run distributions were not measured.
- The public repository is an initial implementation snapshot, not a certified release.
