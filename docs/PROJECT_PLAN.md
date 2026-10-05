# Project Plan

## Goal

Deliver DBeeApp as a small, secure, documented Python CLI that runs declarative PostgreSQL jobs in restricted environments and carries all pure-Python runtime libraries locally without installing them. Public publication target: `lukas-meszaros/DBeeApp`; never overwrite a repository that already exists.

## Phases and Acceptance Criteria

1. **Research and specification**: document dependency/API findings; finalize architecture, Template Specification v1, session and transaction semantics, provider IPC, result handling, errors/retry policy, CLI, and test plan before runtime code.
2. **Parser and validation**: safe single-document YAML loader; strict schema/version validation; static reference/path checks; `validate`, `describe`, and precise `dry-run` semantics without provider/database/output side effects.
3. **Providers**: trusted provider-name resolution; bounded JSON stdin/stdout protocol; dummy provider; CyberArk AIM provider with TLS verification and timeouts.
4. **Database and sessions**: pg8000 DB-API; bind SQL values; lazy `reuse` registry; isolated `new`; override isolation; invalidate broken sessions; exception-safe cleanup.
5. **Workflow and results**: sequential SQL, controlled placeholders/conditions, result modes and bounded streaming, named variables, error policies, per-statement transaction boundaries.
6. **Transactions**: same-connection atomic groups; rollback on child error; no cross-database/new-session children; stop execution after transaction loss.
7. **Outputs and observability**: stdout/file, text/CSV/JSON/JSONL, append/overwrite, structured non-secret logs and failure events.
8. **Testbed and examples**: two isolated PostgreSQL services; seeded deterministic fixtures; at least five working examples, each in its own directory with `job.yaml` and `sql/`; explicit session-state/session-isolation cases.
9. **Documentation and offline packaging**: user/developer/provider/security/session/testing/offline guides, locally vendored source/license workflow, changelog and file index.
10. **Release validation**: unit, integration, security, CLI, lint/type checks, example runs, secret scan, repository review, public repository creation only after all gates pass.

## Release Gates

- Python floor and RHEL target validated on supported interpreters.
- No internet, PyPI, or third-party package installation at runtime; vendored source and licenses are included in the application distribution.
- Template validation occurs before provider calls, connections, SQL, and output creation.
- No password leaks in normal logs/CLI/provider failure surfaces; no SQL retry after ambiguous execution.
- Two independent PostgreSQL services and session/transaction integration tests pass.
- Documentation accurately distinguishes implemented behavior from deferred work.
- `gh repo view lukas-meszaros/DBeeApp` confirms absence before creation; verify public visibility after creation.

## Decisions to Record

- Use pg8000 DB-API named style `:parameter` for parameter values; SQL identifiers are not substitutable.
- Vendor pinned pure-Python runtime packages in the source tree; do not install third-party libraries into runtime Python environments.
- Each workflow lives at `<job-folder>/job.yaml`; external SQL files live at `<job-folder>/sql/...`.
- Provider defaults live in application YAML under `providers.<name>`; per-database `credential.options` overrides those defaults.
- Use PyYAML SafeLoader with duplicate-key rejection and strict unknown properties.
- Provider scripts are administrator-approved standalone scripts; names only, no template paths.
- Connection retry may occur only before SQL is dispatched when known; SQL execution is not retried in v1.
- Public CyberArk AIM docs currently could not be fetched; verify exact AIM Web Service URI/request semantics against the installed CyberArk version before marking that provider integration complete.

## Current Status

Core CLI/workflow, provider boundary, session/transaction behavior, outputs, examples, and local PostgreSQL integration coverage have been implemented. The public source repository exists at `https://github.com/lukas-meszaros/DBeeApp`; no certified release/tag exists yet. Remaining release gates are target RHEL execution, CyberArk version-specific validation, repeated performance/RSS measurements, and final security/artifact review. See `PROGRESS.md` for exact evidence.
