# DBeeApp

**Declarative PostgreSQL workflow runner for secure/offline environments.**

DBeeApp is a lightweight Python CLI for ordered PostgreSQL workflows described in YAML. It uses pg8000, binds SQL values separately, reuses database sessions by default, supports trusted password-provider scripts, and is designed for deployment without runtime internet access.

Repository: [lukas-meszaros/DBeeApp](https://github.com/lukas-meszaros/DBeeApp)

```yaml
version: 1
job:
  id: current_time
databases:
  local:
    host: 127.0.0.1
    database: postgres
    user: app_reader
    credential:
      provider: dummy
      options: {password: test-only}
steps:
  - id: now
    type: sql
    db: local
    sql: SELECT CURRENT_TIMESTAMP AS checked_at
    result: {mode: first}
  - id: print
    type: output
    source: now
    target: {type: stdout}
    format: json
```

```sh
dbeeapp validate job.yaml
dbeeapp describe job.yaml
dbeeapp run job.yaml
```

Implemented features include YAML workflows, PostgreSQL with pg8000, offline dependency bundles, pluggable password providers including CyberArk AIM, safe bound parameters, lazy reusable and isolated sessions, explicit transaction groups, conditions, bounded results, and file/stdout outputs.

The initial implementation is available in this checkout. RHEL certification and CyberArk version-specific integration are still outstanding; see [Project Progress](docs/PROGRESS.md) for verified status and [Offline Installation](docs/OFFLINE_INSTALLATION.md) for the tested local-wheelhouse workflow.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Template Specification v1](docs/TEMPLATE_SPEC_V1.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database Sessions](docs/DATABASE_SESSIONS.md)
- [Password Providers](docs/PASSWORD_PROVIDERS.md)
- [Security](docs/SECURITY.md)
- [Offline Installation](docs/OFFLINE_INSTALLATION.md)
- [Testing](docs/TESTING.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Project Plan](docs/PROJECT_PLAN.md)
- [Progress](docs/PROGRESS.md)

## Security Note

Templates can run SQL using configured database permissions. Review workflows and grant least privilege. `providers/dummy.py` is development/test only. Never commit real secrets or real infrastructure details.
