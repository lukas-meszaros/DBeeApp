# Template Specification v1

This is the contract for YAML workflow templates. A template is data, never executable code. Each job resides in its own directory, conventionally as `job.yaml`, and any related external SQL is under that directory's `sql/` folder. SQL paths resolve against the job file's parent directory. YAML aliases/tags other than standard safe YAML values are not part of the contract. Unknown properties and duplicate keys are errors. Exactly one YAML document is accepted.

## Top Level

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `version` | integer | yes | `1` | Any unsupported version fails before side effects. |
| `job` | mapping | yes | — | Only `id`, `description` are allowed. |
| `job.id` | string | yes | — | `[A-Za-z][A-Za-z0-9_-]*`; unique job name. |
| `job.description` | string | no | empty | Informational; never evaluated. |
| `variables` | mapping string to scalar/list/map | no | `{}` | Initial non-secret values; no reserved `steps`/credential namespace. |
| `databases` | mapping ID to database | yes | — | At least one database; IDs use identifier rule. |
| `steps` | ordered sequence | yes | — | Nonempty; run in declaration order. V1 has no DAG or `depends_on`. |

## Database Properties

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `host` | string | yes | — | Hostname/IP only, not a connection URI. |
| `port` | integer | no | `5432` | 1..65535. |
| `database` | string | yes | — | PostgreSQL database name. |
| `schema` | string | no | server default | Informational only in v1; never identifier-interpolated. |
| `user` | string | yes | — | Username passed to provider and pg8000. |
| `session` | mapping | no | `{mode: reuse}` | Only `mode` is allowed. |
| `session.mode` | string | no | `reuse`; `reuse` or `new` | Default session policy for SQL steps. Session lifetime is independent from transaction lifetime. |
| `credential` | mapping | yes | — | Only `provider`, `options`. |
| `credential.provider` | string | yes | approved provider name | Name only; absolute/relative paths rejected. Must resolve under admin provider directory. |
| `credential.options` | mapping | no | `{}` | Provider-specific database/job overrides. Merged over `application_config.providers.<provider>`; these values take precedence. Do not put a returned database password here. |
| `ssl` | mapping | no | application default, secure verify-full | Strict certificate and hostname verification by default. Only `mode`, `ca_file` allowed. |
| `ssl.mode` | string | no | `verify-full` | `verify-full` or `disable`; disabling requires explicit app policy and should be test-only. |
| `ssl.ca_file` | string | no | platform trust store | CA bundle path; readable and administrator-controlled. |
| `connect_timeout` | number | no | app default | Positive seconds; bounded connection establishment. |

## Step Properties

All IDs are unique across the entire template, including transaction children. Every step may have `id`, optional `when`, and optional `on_error` in addition to the type-specific fields. Unknown fields fail.

### SQL Step

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `type` | string | yes | `sql` | Supported step type. |
| `db` | string | yes | — | Must name a declared database. |
| `session` | mapping | no | database default | Only `mode: reuse|new`; `new` is temporary for this operation and does not replace reusable session. |
| `sql` | string | exactly one source | — | Inline SQL text. |
| `sql_file` | relative path | exactly one source | — | Resolved relative to template directory; traversal/symlink escape, unreadable files, non-UTF-8 files, and files over 1 MiB are rejected during validation. |
| `params` | mapping name to value/reference | no | `{}` | Keys must match named placeholders; values resolve to Python objects and are bound by DB-API; no interpolation. |
| `result` | mapping | no | `{mode: none}` | Only `mode`, `max_rows`, `max_bytes`; mode `none|scalar|first|rows|stream`. |
| `result.max_rows` | positive integer | no | configured cap | Hard safety limit; exceeding it errors, never truncates silently. |
| `result.max_bytes` | positive integer | no | configured cap | Serialized/materialized safety limit. |
| `set` | mapping variable name to reference/value | no | `{}` | Evaluated only after success; writes explicit workflow variables under `vars`. |
| `timeout` | positive number | no | app default | SQL execution timeout, enforced using transaction-local PostgreSQL `statement_timeout`; it is cleared at the transaction boundary and does not make retry safe. |

Result shape: every successful SQL step provides `row_count`, `columns`, `duration`, and `status`; `rows` and `first` exist only when retained by the selected mode. `scalar` requires at most one row and exactly one column when present. `first` is one row mapping or null. `rows` is a list of row mappings. `none` retains no row values. `stream` requires a row-returning SELECT statement, uses a server-side cursor and bounded fetch batches, and must be consumed by the immediately following CSV/JSONL output step on a reusable session. SQL forms unsupported by PostgreSQL cursor declarations fail at execution. Failed and skipped steps have status/error category and no successful result payload.

### Output Step

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `type` | string | yes | `output` | Supported step type. |
| `source` | string | yes | prior SQL step ID | Must reference an earlier successful/non-skipped SQL result; a stream source requires a stream-compatible format. |
| `target` | mapping | yes | — | `type: stdout|file`; file requires path. |
| `target.path` | path | conditional | — | Absolute path only; validated before run. Parent-directory ACLs must be trusted. Symlinks and special files rejected for write targets. |
| `format` | string | yes | `text|csv|json|jsonl` | JSON/JSONL use a documented JSON-safe conversion for dates/decimals/bytes. |
| `mode` | string | no | `append` | `append|overwrite`; ignored for stdout and rejected if specified there. Overwrite is atomic where supported. |
| `text` | string | for text | — | Literal text with limited resolver placeholders; no expressions or secret references. |

Output steps may read `vars` and prior `steps`; no password/credential namespace exists. `stdout` target writes only rendered output. Diagnostics and logs use stderr.

### Transaction Step

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `type` | string | yes | `transaction` | Atomic group, not a session mode. |
| `db` | string | yes | — | One declared database for the group. |
| `steps` | ordered sequence | yes | — | Direct child SQL steps only in v1; each child ID remains globally unique. Same connection for all children. |
| child `db` | string | no | parent db | If present it must equal parent db. |
| child `session` | mapping | forbidden | — | No per-child session override; transaction owns connection. |
| child `type` | string | required | `sql` | Nested transactions and outputs are not allowed. |
| child result | mapping | allowed | standard result contract | Streaming child results are disallowed in v1. |
| parent `session` | mapping | forbidden | — | Group uses the database's reusable connection (or a single isolated group connection only if v1 implementation explicitly supports this; initial implementation uses reusable). |

The engine begins one DB-API transaction before the first child, commits only after all children succeed, otherwise rolls back if possible. It never continues after a connection loss. Results become visible in context only after each child completes; the group status is failed if any child or commit fails. No cross-database group and no SQL `BEGIN`/`COMMIT`/`ROLLBACK` control inside DBeeApp transaction groups.

## Common Properties

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `when` | one-key mapping | no | always | Exactly one supported operator. Evaluated before acquiring credentials/connections. A false result marks step `skipped`. |
| `on_error.action` | string | no | `fail`; `fail|continue` | `continue` is allowed only for a non-transaction step; transactions always fail atomically. |
| `on_error.retries` | integer | no | `0` | V1 must be zero for SQL execution. Nonzero is rejected; never repeat SQL after dispatch. Provider/connect retry policy is application configuration and separately bounded. |

Conditions: `equals`, `not_equals`, `greater_than`, `greater_than_or_equal`, `less_than`, `less_than_or_equal`, `contains`, `empty`, `not_empty`, `success`, `failure`, and `row_count`. Each has strict operand shape documented in the implementation docs. Comparisons do not evaluate arbitrary expressions; incompatible values are validation/runtime condition errors. A step reference must point to an earlier step, preventing forward/circular references.

## Variable Resolver

Only complete placeholders matching `{{ vars.NAME }}` or `{{ steps.ID.FIELD[.FIELD...] }}` are valid. No filters, calls, methods, arithmetic, blocks, interpolation in SQL text, or arbitrary Python. Placeholder values are resolved as values, preserving non-string scalar types when the entire value is a placeholder. Literal text templating is only available for `output.text`. Undefined names, future-step references, and unknown result properties fail validation when static or fail before that step at runtime. Passwords and credential properties are never addressable.

## Application Configuration

Application configuration is external to each job. It owns provider directory, global timeouts, provider-specific defaults under `providers.<provider_name>`, default database session mode (`reuse` or `new`, default `reuse`), fetch batch size, row/output ceilings, TLS defaults, logging/failure-log settings, and default result settings. Provider names map to arbitrary option mappings passed to that provider. At connection time, DBeeApp merges application provider defaults with `credential.options`; database/job values win on duplicate keys. It rejects unknown application-level keys. Database and step overrides take precedence over the global session default. A transaction group requires a reusable database session. Template overrides may not disable required security controls. The example file is never auto-loaded; a config file must be selected explicitly with CLI `--config`.

Application-config provider fields:

| Property | Type | Required | Default / allowed | Rules |
| --- | --- | --- | --- | --- |
| `providers` | mapping provider name to mapping | no | `{}` | Provider names use `[a-z][a-z0-9_]*`; keys are matched to `credential.provider`. |
| `providers.<name>` | mapping string to JSON-compatible values | no | `{}` | Passed as defaults to the named provider; the provider validates its own option keys. |
| `credential.options` | mapping string to JSON-compatible values | no | `{}` | Per-database values overlay `providers.<credential.provider>` for duplicate keys. |

The application config file is selected only with `--config PATH`; neither `dbeeapp.yaml.example` nor the testbed file is auto-discovered.

## Exit Codes

`0` success; `2` CLI/usage; `3` configuration/template validation; `4` provider; `5` connection; `6` SQL/transaction; `7` output; `8` internal failure; `130` keyboard interruption. User-facing errors are concise, categorized, and do not include secrets or raw provider/database payloads.

## Example

```yaml
version: 1
job:
  id: application_status
variables:
  application: TEST_APP
databases:
  control:
    host: 127.0.0.1
    database: control
    user: control_user
    credential:
      provider: dummy
      options: {password: test-only}
steps:
  - id: lookup
    type: sql
    db: control
    sql: SELECT application_id FROM applications WHERE application_name = :application
    params:
      application: "{{ vars.application }}"
    result: {mode: first}
    set:
      application_id: "{{ steps.lookup.first.application_id }}"
  - id: report
    type: output
    source: lookup
    target: {type: stdout}
    format: text
    text: "{{ vars.application }}={{ vars.application_id }}"
```
