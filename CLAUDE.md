# DBeeApp AI Session Instructions

Before changing architecture or code, read these in order:

1. `CLAUDE.md`
2. `docs/FILE_INDEX.md`
3. `docs/ARCHITECTURE.md`
4. `docs/TEMPLATE_SPEC_V1.md`
5. `docs/PROGRESS.md`

## Project Principles

DBeeApp is a short-lived, sequential Python CLI for declarative PostgreSQL workflows, intended for RHEL and restricted/offline environments. Prefer explicit contracts, safe defaults, low memory, minimal dependencies, and easy-to-audit code. Do not add a daemon, web service, scheduler, ORM, pool, concurrency, arbitrary expressions, or full template engine.

## Security Rules

Templates are data, never code. Use safe YAML loading, strict unknown-field rejection, named DB-API parameters, safe template-relative SQL paths, and an administrator-controlled provider directory with validated names. Never place a password in workflow context, output, errors, logs, argv, or provider stderr. Provider scripts are trusted executable code installed by an administrator. Do not expose raw third-party exception text without reviewing it for secrets.

Runtime Python libraries are vendored under `dbeeapp/_vendor`; never add a runtime pip-install step. Refresh them only from exact local wheel pins using `tools/vendor_runtime.py`, preserve licenses, and verify imports under `python -S`.

## Database Rules

`session.mode: reuse` lazily opens and retains one connection per database ID until job cleanup. `new` opens an isolated connection for one operation and closes it without replacing the reusable connection. Session lifetime and transaction boundaries are distinct. Transaction groups must use one database and one connection; a child failure rolls the group back and prevents later children. Never automatically repeat SQL after execution may have begun. A lost connection invalidates that session; do not silently reconnect and continue a workflow.

## Coding and Testing

Use typed, cohesive Python modules and explicit application exceptions. Keep Python compatibility at the documented floor. Add focused unit tests for changed behavior and integration tests for database/session/transaction contracts. Run unit tests and applicable PostgreSQL integration tests before claiming success. Never claim unrun checks passed.

## Documentation Maintenance

Update `docs/PROGRESS.md` after meaningful milestones and keep `docs/FILE_INDEX.md`, `docs/ARCHITECTURE.md`, `docs/TEMPLATE_SPEC_V1.md`, `docs/CHANGELOG.md`, examples, and user/security docs aligned with behavior. For an architectural change, edit its spec before or with the implementation.

## Commands

- Unit tests without site packages: `python3 -S -m unittest discover -s tests -v`
- Start integration DBs: `docker compose -f testbed/compose.yaml up -d`
- CLI from checkout: `python3 -S -m dbeeapp`
- Verify local runtime dependencies without site packages: `python3 -S -m dbeeapp version`
- Refresh vendored libraries from local wheel files: `python3 tools/vendor_runtime.py --wheelhouse wheelhouse --replace`

## Ownership Map

See `docs/FILE_INDEX.md`. Keep the CLI thin; template parsing/validation, resolution, provider invocation, database sessions, workflow execution, outputs, and errors belong to their respective modules, not one monolithic file.
