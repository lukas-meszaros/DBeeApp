# Changelog

All notable changes are recorded here. The public source repository is active; no certified release version has been tagged.

## Unreleased

- Published the initial implementation snapshot to the public GitHub repository; no certified release tag has been created.
- Implemented Python CLI commands `version`, `validate`, `describe`, and `run` with side-effect-free dry-run.
- Added Template Specification v1 validation, safe YAML, bounded resolver/conditions, SQL parameter binding, result limits/streaming, file/stdout formats, session reuse/new, and transaction groups.
- Added dummy and CyberArk AIM provider scripts behind a bounded JSON subprocess protocol.
- Added ten examples and a two-instance PostgreSQL testbed with unit and opt-in integration tests.
- Runtime dependency code is vendored locally, and examples now use one folder per job with an adjacent `sql/` folder.
- Added application YAML provider defaults with per-database override precedence; renamed config templates to `dbeeapp.yaml.example` and `dbeeapp.testbed.yaml`.
- Expanded `steps[].result.mode` documentation with mode-specific shapes, empty behavior, limits, and stream requirements; `first` and `scalar` now avoid retaining unnecessary rows.
- Recorded architecture, security, session, provider protocol, offline deployment, user and developer guidance.
- The initial implementation is published but not RHEL/CyberArk certified; see `docs/PROGRESS.md` for outstanding release gates.
