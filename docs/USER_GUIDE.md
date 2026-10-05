# User Guide

## Status

This guide describes Template Specification v1. Consult `PROGRESS.md` for the verified feature set and remaining target-environment limitations.

## Install and Run

Runtime Python libraries are bundled in `dbeeapp/_vendor`; no runtime `pip install` is performed. From a source checkout or extracted source bundle, invoke the module directly:

```sh
python3 -S -m dbeeapp version
python3 -S -m dbeeapp validate templates/my_job/job.yaml
python3 -S -m dbeeapp describe templates/my_job/job.yaml
python3 -S -m dbeeapp run templates/my_job/job.yaml
```

`validate` checks configuration and template statically without requesting passwords or connecting. `describe` prints job/database/step/session metadata and never secrets. `run` validates fully, then executes steps in order. Errors go to stderr; step output goes to its configured target. Exit codes are listed in `TEMPLATE_SPEC_V1.md`. `-S` disables Python's site initialization and is useful for verifying runtime dependencies came only from the local vendor tree.

## Workflow Shape

A template begins with `version: 1`, a job ID, optional variables, database definitions, and ordered steps. Keep each job in its own directory as `job.yaml`; store related SQL files in that job's `sql/` directory. Unknown keys are errors. A step can use only earlier step results; v1 does not have parallel steps or a dependency graph.

```yaml
version: 1
job:
  id: find_application
  description: Look up a configured application
variables:
  application: TEST_APP
databases:
  control:
    host: db.example.invalid
    port: 5432
    database: control
    user: app_reader
    session: {mode: reuse}
    credential:
      provider: dummy
      options: {password: test-only}
steps:
  - id: lookup
    type: sql
    db: control
    sql: |
      SELECT application_id, application_name
      FROM applications
      WHERE application_name = :application
    params:
      application: "{{ vars.application }}"
    result: {mode: first}
    set:
      application_id: "{{ steps.lookup.first.application_id }}"
  - id: show
    type: output
    source: lookup
    target: {type: stdout}
    format: text
    text: "Application {{ vars.application }} has ID {{ vars.application_id }}"
```

## Databases and Credentials

Every database declares host, database name, user, credential provider, and optional port/session/TLS/timeout settings. Passwords are fetched only when a connection is needed. Provider names are fixed identifiers, not paths. The dummy provider is for tests only; use the approved provider for production. Never put a password literal in a committed workflow.

Application configuration may set a global `session.mode` default. A database-level `session.mode` overrides it, and an individual SQL step may request `new` without replacing an existing reusable connection. Transactions require a reusable database session.

Provider defaults are also application-configurable. Put shared provider settings under `providers.<provider_name>` in the application config, then use each database's `credential.options` for job-specific settings. Per-database options override application defaults. The file [config/dbeeapp.yaml.example](../config/dbeeapp.yaml.example) is an inert example only; DBeeApp does not discover or load it automatically. Copy it to an administrator-managed location, set real environment-specific values, and pass its path explicitly with `--config`.

The file [config/dbeeapp.testbed.yaml](../config/dbeeapp.testbed.yaml) is for the local Docker testbed only. It disables PostgreSQL TLS verification and logging for local test runs; it is not a production baseline.

PostgreSQL TLS verification is strict by default. Configure a trusted CA bundle where needed; do not disable verification to bypass a certificate error.

## Sessions and Transactions

The default `session.mode` is `reuse`: open lazily and reuse one PostgreSQL connection per database. This preserves temporary tables and connection-level `SET` state across steps. `new` creates and closes a separate session for each operation. A step can override the database's default with `session: {mode: new}` without replacing the reusable connection. See `DATABASE_SESSIONS.md`.

A session is not a transaction. Standalone steps commit/rollback their own transaction. A `type: transaction` step groups multiple SQL children on one database connection and commits as a unit or rolls back on failure.

## SQL and Parameters

Use inline `sql` or a template-relative `sql_file`, never both. The supported named placeholder form is `:name`; values go in `params` and are passed to pg8000 separately. This is for SQL values only, not table/schema/column identifiers. Do not quote placeholders in SQL.

```yaml
sql: SELECT * FROM customer WHERE customer_id = :customer_id
params:
  customer_id: "{{ vars.customer_id }}"
```

External SQL paths cannot escape the template directory; files must be readable UTF-8 and at most 1 MiB. Keep SQL files beside the job in a `sql/` subdirectory.

## Results and Variables

`result.mode` is one of `none`, `scalar`, `first`, `rows`, or `stream`. Choose the smallest mode that meets the job's needs. Safety caps fail explicitly rather than silently dropping rows. SQL steps expose metadata and available result values under `steps.ID`; `set` explicitly promotes a value into workflow variables under `vars`. Initial variables and resolved results are non-secret workflow data.

`stream` is for row-returning SELECT queries. DBeeApp uses a PostgreSQL server-side cursor and bounded fetch batches, then requires the immediately following step to write CSV or JSONL. The database session remains open until that output drains or closes the stream.

Only simple complete placeholders are supported. No Python expressions, function calls, loops, or arbitrary Jinja syntax.

## Conditions and Failures

`when` accepts one of the documented declarative conditions in the spec. A false condition marks the step `skipped`; later references to unavailable values fail clearly. `on_error.action` is `fail` (default) or `continue` where allowed. V1 does not retry SQL: after a timeout or connection loss, PostgreSQL may already have executed a modifying statement.

## Outputs

An output step refers to a previous SQL step and writes text, CSV, JSON, or JSONL to stdout or an explicitly configured file. File paths and formats are validated before execution. Append is the default; overwrite is atomic where the filesystem allows. Protect output directories with OS permissions. Do not render secrets; they are unavailable in template context.

## Timeouts and Logging

Application config provides finite provider, connection, and SQL timeout defaults. A SQL timeout stops/warns on the operation but is not proof it did not run. Structured logs include operational IDs, status, duration, and error category only, not SQL parameters or passwords. See `SECURITY.md` and the application config reference as implemented.
