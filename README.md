# DBeeApp

**Declarative PostgreSQL workflow runner for secure/offline environments.**

DBeeApp is a lightweight Python CLI for ordered PostgreSQL workflows described in YAML. It uses locally vendored pg8000/PyYAML and their pure-Python dependencies, binds SQL values separately, reuses database sessions by default, supports trusted password-provider scripts, and runs without installing runtime libraries into Python or accessing the network.

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
python3 -S -m dbeeapp validate job.yaml
python3 -S -m dbeeapp describe job.yaml
python3 -S -m dbeeapp run job.yaml
```

Application config is not auto-discovered. Start from [config/dbeeapp.yaml.example](config/dbeeapp.yaml.example), place the configured copy in an administrator-managed path, then pass it explicitly before the command, for example:

```sh
python3 -S -m dbeeapp --config /etc/dbeeapp/dbeeapp.yaml validate /path/to/my_job/job.yaml
```

Shared provider defaults go under `providers.<provider_name>` in that application YAML; database-specific overrides go under `databases.<id>.credential.options` in the job YAML. `config/dbeeapp.testbed.yaml` is only for the local Docker testbed and deliberately disables PostgreSQL TLS verification.

From a source checkout, run `python -m dbeeapp ...`. Runtime library modules are included under `dbeeapp/_vendor` and loaded from that directory; no `pip install` of runtime requirements is needed. For the expected job-directory layout, see the folders under [examples](examples/).

Implemented features include YAML workflows, PostgreSQL with locally sourced pg8000, no runtime package installation, pluggable password providers including CyberArk AIM, safe bound parameters, lazy reusable and isolated sessions, explicit transaction groups, conditions, bounded results, and file/stdout outputs.

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
