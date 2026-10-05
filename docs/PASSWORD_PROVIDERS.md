# Password Providers

## Trust Boundary

A provider is an administrator-installed executable script, not a template plugin. Installing or changing one is equivalent to installing application code. Templates can select only an approved simple provider name, never a path or command. The configured provider directory and scripts must be owned/writable only by administrators and have restrictive permissions.

## Protocol v1

DBeeApp starts the provider with a fixed argv (script path only, no secret arguments), `shell=False`, a minimal documented environment, stdin/stdout/stderr pipes, and a configured timeout. Provider-specific non-secret options are supplied as JSON on stdin. Passwords never appear in argv, environment variables, logs, or workflow context.

Request (UTF-8 JSON, exactly one object):

```json
{"version":1,"username":"report_user","options":{"app_id":"DBeeApp","safe":"DB_TEST","folder":"Root"}}
```

Success response on stdout, exactly one JSON object and no other output:

```json
{"version":1,"password":"development-only"}
```

Exit status `0` means success; any nonzero value means provider failure. A success response must include version 1 and a non-empty string password, with no unknown keys. Malformed JSON, extra stdout bytes/lines, invalid UTF-8, timeout, nonzero status, invalid schema, or empty password fails closed. Providers write diagnostic details only to stderr; DBeeApp does not forward stderr because it could contain secrets. The error presented to the user is a generic provider category plus provider name and safe exit/timeout status.

Output and input sizes are capped. The child is terminated/killed and reaped on timeout/interruption. Do not inherit secrets through an uncontrolled environment; only necessary environment variables are passed. A provider must not print credential responses, request headers, or secrets.

## Provider Requirements

- Standalone Python script; standard library only is preferred.
- Read one request from stdin; validate its protocol version and fields.
- Return one JSON response on stdout and nothing else on success.
- Do not accept password in command-line arguments.
- Validate all configured values; use HTTPS with certificate and hostname verification and finite connect/read timeouts for network calls.
- Do not log the returned password or sensitive API payloads.
- Fail with nonzero status and useful stderr for operators, while DBeeApp treats stderr as sensitive and does not display it.

## Dummy Provider

`providers/dummy.py` exists only for local development/testbed examples. It returns the explicitly configured `options.password` and is not suitable for production. Never place a real credential in a committed template. The configured test secret is intentionally dummy-only.

## CyberArk AIM

`providers/cyberark_aim.py` uses the CyberArk AIM Web Service from a configured base URL with `AppID`, `Safe`, `Folder`, and account/user lookup values. The base URL, TLS CA, and timeouts are configuration, not hardcoded infrastructure. TLS verification is mandatory. Response content and returned secret are never written to stderr/stdout except the protocol response. Public documentation URLs attempted during initial research returned 404; before declaring compatibility, verify the exact URL path, parameter names, response schema, and supported server version against authoritative CyberArk documentation or the deployment's known-good AIM Web Service configuration.

Example options shape:

```yaml
credential:
    provider: cyberark_aim
    options:
        base_url: https://vault.example.invalid
        app_id: DBeeApp
        safe: DB_TEST
        folder: Root
        account_parameter: Object
        ca_file: /etc/pki/tls/certs/corporate-ca.pem
        timeout: 10
```

`base_url` is the HTTPS origin/context prefix; the script appends `/AIMWebService/api/Accounts`. `account_parameter` is restricted to `Object` or `UserName`. Confirm these details against the installed AIM release before production use.

## Example Skeleton

```python
#!/usr/bin/env python3
import json
import sys

request = json.load(sys.stdin)
if request.get("version") != 1:
    raise SystemExit(2)
password = "development-only"  # Replace with a trusted secret source.
json.dump({"version": 1, "password": password}, sys.stdout)
sys.stdout.write("\n")
```

The skeleton is illustrative; production providers must validate the entire request and contain exceptions so secrets cannot leak through tracebacks.
