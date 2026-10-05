# Security

## Threat Model

Templates and SQL files may be authored by workflow users and are treated as untrusted data relative to the DBeeApp process. Application configuration, provider scripts, Python packages, and output directories are administrator-controlled trusted assets. A template can request SQL execution with the configured database identity; DBeeApp cannot infer whether arbitrary SQL is operationally safe, so template review and least-privilege database roles remain essential.

## Controls

- PyYAML safe loading only; exactly one document; reject aliases, custom/unsafe tags, duplicate keys, and unknown properties.
- Restricted placeholder resolver; no `eval`, `exec`, Python import, function calls, or full Jinja.
- Named parameter binding for SQL values; no identifier interpolation or SQL string formatting.
- SQL file canonical path must remain inside the template root; reject traversal and symlink escape.
- SQL source files are size-limited and checked for UTF-8 readability during validation, before providers or connections are invoked.
- Provider IDs are validated names resolved inside a fixed administrator-owned directory; no user-provided executable path; subprocess without shell and no secrets in argv.
- Passwords remain out of context, outputs, CLI descriptions, and logs. Provider stdout is parsed under a strict bounded protocol; stderr is not forwarded. Database exceptions are normalized to avoid accidental sensitive payload exposure.
- PostgreSQL server-message forwarding is disabled by default. When opted in, only severity and primary message are routed; message size and per-connection buffer are bounded. SQL authors must never put secrets in `RAISE` messages because an enabled destination can disclose them.
- Provider and database HTTPS/TLS certificate verification enabled; finite connection/request/provider timeouts.
- PostgreSQL connections use explicit secure TLS configuration; no silent insecure fallback.
- Row, output, SQL, and provider IPC limits bound memory and execution.
- No automatic replay of SQL after request dispatch may have occurred.
- Output file paths require trusted parent directory permissions; overwrite uses atomic replace where feasible.

## Operational Requirements

Protect application config and provider scripts with OS permissions. Do not commit real passwords, CyberArk AppIDs/Safes/URLs that identify real infrastructure, production SQL, logs, wheelhouse artifacts containing private source, or local environment files. Use least-privilege PostgreSQL accounts, restrict provider network access, and rotate credentials in the external secret system. Treat core dumps and process memory as potentially sensitive.

## Limitations

A database administrator or authorized SQL template can still perform destructive operations within the granted SQL privileges. DBeeApp does not parse SQL to prove read-only behavior. Python cannot guarantee secure zeroization of immutable password strings. A timed-out SQL statement may have executed before the client observed the timeout; timeout is not a retry-safety signal.
