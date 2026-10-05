# File Index

This index reflects the current project structure and implemented ownership boundaries.

## Root

| File | Purpose / ownership | Dependencies / when to modify |
| --- | --- | --- |
| `CLAUDE.md` | Required AI continuation instructions and project invariants. | Update if workflow/security/testing conventions change. |
| `README.md` | First-use overview and quick start. | Links to user/spec/security/offline documentation. |
| `pyproject.toml` | Package metadata, CLI entry point, runtime dependency pins. | Modify when packaging/API/dependencies change. |
| `requirements-runtime.txt` | Exact production dependency closure. | Update with dependency lock and wheelhouse instructions. |
| `requirements-dev.txt` | Development/test dependencies only. | Keep separate from production. |
| `MANIFEST.in` | Source package inclusion rules. | Update when packaged assets/providers change. |
| `.gitignore` | Excludes local envs, secrets, logs, coverage/build artifacts. | Review before release. |

## Documentation

| File | Purpose / ownership | Dependencies / when to modify |
| --- | --- | --- |
| `docs/PROJECT_PLAN.md` | Phases, acceptance criteria, decisions, release gates. | Update as milestones and scope change. |
| `docs/PROGRESS.md` | Current phase, completed work, test status, risks. | Update every meaningful milestone. |
| `docs/ARCHITECTURE.md` | Components, lifecycle, session/transaction/provider design. | Update for behavior/structure changes. |
| `docs/TEMPLATE_SPEC_V1.md` | Authoritative YAML contract. | Any template behavior change requires spec review. |
| `docs/FILE_INDEX.md` | Repository navigation and module ownership. | Update whenever structure changes. |
| `docs/PASSWORD_PROVIDERS.md` | Provider protocol, security boundary, examples. | Provider protocol/implementation changes. |
| `docs/DATABASE_SESSIONS.md` | Session vs transaction semantics, reuse/new and cleanup. | Session manager behavior changes. |
| `docs/SECURITY.md` | Threat model, secret handling, trusted code boundary. | Security changes and release review. |
| `docs/TESTING.md` | Unit/integration/security testing and testbed commands. | Test strategy/service changes. |
| `docs/PERFORMANCE.md` | Performance goals and local benchmark observations. | Update after repeated measurements or result/session design changes. |
| `docs/OFFLINE_INSTALLATION.md` | Locked, hash-verified offline wheelhouse workflow. | Runtime dependencies/install procedure change. |
| `docs/USER_GUIDE.md` | User-facing workflow creation and CLI guide. | CLI/template feature changes. |
| `docs/DEVELOPER_GUIDE.md` | Contributor architecture, tests, coding workflow. | Development conventions change. |
| `docs/CHANGELOG.md` | User-visible changes by release. | Every release or notable change. |

## Runtime ownership

| Path | Responsibility | Dependencies / when to modify |
| --- | --- | --- |
| `dbeeapp/cli.py`, `dbeeapp/__main__.py` | CLI, exit codes, command routing. | Config/loader/engine; CLI behavior changes. |
| `dbeeapp/config.py` | Strict application config and defaults. | stdlib/PyYAML; operational configuration changes. |
| `dbeeapp/template_loader.py` | Safe YAML parsing and source paths. | PyYAML; parsing/security changes. |
| `dbeeapp/validator.py` | Static schema/reference/path validation and describe model. | Spec contract changes. |
| `dbeeapp/resolver.py`, `dbeeapp/conditions.py` | Restricted value placeholders and condition operators. | Template evaluation changes. |
| `dbeeapp/errors.py` | Error taxonomy and public-safe diagnostics. | Error/exit behavior changes. |
| `dbeeapp/credentials.py` | Approved provider resolution and bounded IPC. | Provider protocol changes. |
| `dbeeapp/database.py`, `dbeeapp/sessions.py` | pg8000 adapter, session registry, cleanup, error classification. | DB/session/parameter lifecycle changes. |
| `dbeeapp/results.py` | Result shape, row conversion, caps/stream handling. | Result modes/memory contracts. |
| `dbeeapp/engine.py` | Ordered workflow execution, transaction groups, and status/context ownership. | Workflow or transaction semantics changes. |
| `dbeeapp/outputs.py` | Text/CSV/JSON/JSONL rendering and targets. | Output behavior changes. |
| `dbeeapp/engine.py` | Structured secret-safe logging setup and failure logging. | Logging behavior changes. |
| `providers/dummy.py`, `providers/cyberark_aim.py` | Standalone trusted provider scripts. | Provider-specific behavior changes; never import engine internals. |

## Runtime (implemented)

| File | Purpose / ownership | Tests |
| --- | --- | --- |
| `dbeeapp/__init__.py`, `dbeeapp/__main__.py` | Version and `python -m dbeeapp` entry point. | `tests/test_cli.py` |
| `dbeeapp/cli.py` | CLI commands, static preflight, exit status and dry-run. | `tests/test_cli.py` |
| `dbeeapp/config.py` | Application-level operational config and defaults, including default session mode. | `tests/test_config.py` |
| `dbeeapp/template_loader.py` | Bounded safe YAML loader; rejects duplicate keys, aliases and multiple documents. | `tests/test_template_loader.py` |
| `dbeeapp/validator.py` | Strict Template v1 checks, paths, provider presence, references, session/transaction/stream pairing, describe output. | `tests/test_validator.py`, `tests/test_cli.py` |
| `dbeeapp/resolver.py`, `dbeeapp/conditions.py` | Typed placeholder resolution, output text and condition operators. | `tests/test_resolver.py` |
| `dbeeapp/errors.py` | Public-safe exception taxonomy and exit codes. | `tests/test_errors.py` |
| `dbeeapp/credentials.py` | Bounded JSON stdin/stdout provider subprocess runner; kills/reaps timeout. | `tests/test_credentials.py` |
| `dbeeapp/database.py` | pg8000 DB-API named binding, TLS, timeout, SQLSTATE classification, commit/rollback. | `tests/test_engine.py`, `tests/test_postgres_integration.py` |
| `dbeeapp/sessions.py` | Lazy reuse/new session registry, invalidation, cleanup. | `tests/test_sessions.py`, `tests/test_postgres_integration.py` |
| `dbeeapp/results.py` | Bounded materialized and batched streaming results, JSON conversion. | `tests/test_results.py`, `tests/test_postgres_integration.py` |
| `dbeeapp/engine.py` | Sequential steps, variables, conditions, session and transaction orchestration. | `tests/test_engine.py`, `tests/test_postgres_integration.py` |
| `dbeeapp/outputs.py` | Bounded stdout/file text, CSV, JSON, JSONL; atomic overwrite. | `tests/test_outputs.py` |
| `providers/dummy.py` | Test-only password provider. | `tests/test_credentials.py` |
| `providers/cyberark_aim.py` | HTTPS CyberArk AIM account retrieval provider; endpoint contract needs target-version confirmation. | Manual/provider follow-up |
| `config/dbeeapp.example.yaml`, `config/testbed.yaml` | Production-shaped config example and explicit insecure local test configuration. | `tests/test_config.py`, integration tests |

## Tests and Testbed

| File / path | Purpose |
| --- | --- |
| `tests/test_cli.py`, `tests/test_config.py`, `tests/test_template_loader.py`, `tests/test_validator.py` | CLI/config/parser/schema/preflight tests. |
| `tests/test_credentials.py` | Provider process protocol, timeout, malformed output and secret diagnostics. |
| `tests/test_resolver.py`, `tests/test_results.py`, `tests/test_outputs.py` | Values, conditions, limits, stream and output-format tests. |
| `tests/test_sessions.py`, `tests/test_engine.py`, `tests/test_errors.py` | Fake-DB lifecycle, workflows, transactions, taxonomy. |
| `tests/test_postgres_integration.py` | Opt-in tests against both live testbed PostgreSQL services. |
| `testbed/compose.yaml` | Two independent PostgreSQL 16.4 containers bound to loopback ports 55432/55433. |
| `testbed/init/control.sql`, `testbed/init/reporting.sql` | Test-only roles, schemas and deterministic fixture data. |
| `examples/*.yaml`, `examples/sql/application_details.sql` | Ten complete workflow templates and their SQL asset, including a 20-step sequential benchmark. |
