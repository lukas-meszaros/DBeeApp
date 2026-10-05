# Changelog

All notable changes are recorded here. The project is in pre-implementation design; no released version exists.

## Unreleased

- Published the initial implementation snapshot to the public GitHub repository; no certified release tag has been created.
- Implemented Python CLI commands `version`, `validate`, `describe`, and `run` with side-effect-free dry-run.
- Added Template Specification v1 validation, safe YAML, bounded resolver/conditions, SQL parameter binding, result limits/streaming, file/stdout formats, session reuse/new, and transaction groups.
- Added dummy and CyberArk AIM provider scripts behind a bounded JSON subprocess protocol.
- Added ten examples and a two-instance PostgreSQL testbed with unit and opt-in integration tests.
- Runtime dependency code is vendored locally, and examples now use one folder per job with an adjacent `sql/` folder.
- Verified local dependency sourcing under Python 3.9.6 with `-S`; all 69 tests, including five PostgreSQL integration tests, passed without installing runtime libraries.
- Recorded architecture, security, session, provider protocol, offline deployment, user and developer guidance.
- Release is not yet certified or published; see `docs/PROGRESS.md` for outstanding gates.
