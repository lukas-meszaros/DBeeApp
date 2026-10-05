"""Static validation for Template Specification v1."""

import re
import os
from pathlib import Path

from dbeeapp.errors import ValidationError

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_PROVIDER = re.compile(r"^[a-z][a-z0-9_]*$")
_PLACEHOLDER = re.compile(r"^\{\{\s*([A-Za-z][A-Za-z0-9_.-]*)\s*\}\}$")
_ANY_PLACEHOLDER = re.compile(r"\{\{.*?\}\}")

_TOP_KEYS = {"version", "job", "variables", "databases", "steps"}
_DATABASE_KEYS = {
    "host", "port", "database", "schema", "user", "session", "credential",
    "ssl", "connect_timeout",
}
_STEP_COMMON_KEYS = {"id", "type", "when", "on_error"}
_SQL_KEYS = _STEP_COMMON_KEYS | {
    "db", "session", "sql", "sql_file", "params", "result", "set", "timeout",
}
_OUTPUT_KEYS = _STEP_COMMON_KEYS | {"source", "target", "format", "mode", "text"}
_TRANSACTION_KEYS = _STEP_COMMON_KEYS | {"db", "steps"}
_RESULT_KEYS = {"mode", "max_rows", "max_bytes"}
_CONDITION_KEYS = {
    "equals", "not_equals", "greater_than", "greater_than_or_equal",
    "less_than", "less_than_or_equal", "contains", "empty", "not_empty",
    "success", "failure", "row_count",
}
_MAX_SQL_FILE_BYTES = 1024 * 1024
_RESERVED_SECRET_NAMES = {"password", "passwd", "secret", "credential", "credentials"}


def _mapping(value, location):
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValidationError("{} must be a mapping with string keys".format(location))
    return value


def _keys(value, allowed, required, location):
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        raise ValidationError("{} has unknown field(s): {}".format(location, ", ".join(sorted(unknown))))
    if missing:
        raise ValidationError("{} is missing required field(s): {}".format(location, ", ".join(sorted(missing))))


def _name(value, location):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValidationError("{} must be an identifier beginning with a letter".format(location))


def _positive_number(value, location):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValidationError("{} must be a positive number".format(location))


def _positive_integer(value, location):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError("{} must be a positive integer".format(location))


def _check_reference(value, location, known_steps, known_variables, current_id=None, mixed=False, allow_result=False):
    if not isinstance(value, str):
        return
    match = _PLACEHOLDER.fullmatch(value)
    if match:
        reference = match.group(1).split(".")
        root = reference[0]
        if root == "result" and allow_result and len(reference) == 1:
            return
        if root == "vars":
            if len(reference) < 2 or reference[1] not in known_variables:
                raise ValidationError("{} references an undefined workflow variable".format(location))
            return
        if root == "steps":
            if len(reference) < 3:
                raise ValidationError("{} has an incomplete step reference".format(location))
            step_id = reference[1]
            if step_id == current_id:
                return
            if step_id not in known_steps:
                raise ValidationError("{} references an unknown or later step".format(location))
            return
        raise ValidationError("{} uses an unsupported reference namespace".format(location))
    if _ANY_PLACEHOLDER.search(value) or "{{" in value or "}}" in value:
        if mixed:
            for found in _ANY_PLACEHOLDER.finditer(value):
                _check_reference(found.group(0), location, known_steps, known_variables, current_id, allow_result=allow_result)
            return
        raise ValidationError("{} must use one complete supported placeholder".format(location))


def _safe_sql_file(value, root, location):
    if not isinstance(value, str) or not value:
        raise ValidationError("{} must be a non-empty relative path".format(location))
    relative = Path(value)
    if relative.is_absolute():
        raise ValidationError("{} must be relative to the template directory".format(location))
    try:
        resolved_root = root.resolve(strict=True)
        resolved_file = (resolved_root / relative).resolve(strict=True)
        resolved_file.relative_to(resolved_root)
    except (OSError, ValueError):
        raise ValidationError("{} is missing or escapes the template directory".format(location)) from None
    if not resolved_file.is_file():
        raise ValidationError("{} must refer to a regular SQL file".format(location))
    try:
        contents = resolved_file.read_bytes()
    except OSError:
        raise ValidationError("{} is not readable".format(location)) from None
    if len(contents) > _MAX_SQL_FILE_BYTES:
        raise ValidationError("{} exceeds the {} byte limit".format(location, _MAX_SQL_FILE_BYTES))
    try:
        contents.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError("{} must contain UTF-8 SQL".format(location)) from None
    return resolved_file


def _check_condition(condition, location, known_steps, known_variables):
    condition = _mapping(condition, location)
    if len(condition) != 1:
        raise ValidationError("{} must contain exactly one condition operator".format(location))
    operator, operands = next(iter(condition.items()))
    if operator not in _CONDITION_KEYS:
        raise ValidationError("{} uses an unsupported condition operator".format(location))
    if operator in {"equals", "not_equals", "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal", "contains"}:
        operands = _mapping(operands, location + "." + operator)
        _keys(operands, {"left", "right"}, {"left", "right"}, location + "." + operator)
        _check_reference(operands["left"], location, known_steps, known_variables)
        _check_reference(operands["right"], location, known_steps, known_variables)
    elif operator in {"empty", "not_empty", "success", "failure"}:
        _check_reference(operands, location, known_steps, known_variables)
    else:
        operands = _mapping(operands, location + ".row_count")
        _keys(operands, {"step", "operator", "value"}, {"step", "operator", "value"}, location + ".row_count")
        _name(operands["step"], location + ".row_count.step")
        if operands["step"] not in known_steps:
            raise ValidationError("{} row_count must reference an earlier step".format(location))
        if operands["operator"] not in {"eq", "ne", "gt", "gte", "lt", "lte"}:
            raise ValidationError("{} row_count operator is invalid".format(location))
        if isinstance(operands["value"], bool) or not isinstance(operands["value"], int) or operands["value"] < 0:
            raise ValidationError("{}.row_count.value must be a non-negative integer".format(location))


def validate_template(document, template_path, config=None):
    """Validate a parsed template and return its normalized source mapping."""
    document = _mapping(document, "template")
    _keys(document, _TOP_KEYS, {"version", "job", "databases", "steps"}, "template")
    if document["version"] != 1 or isinstance(document["version"], bool):
        raise ValidationError("unsupported template version; expected version: 1")

    job = _mapping(document["job"], "job")
    _keys(job, {"id", "description"}, {"id"}, "job")
    _name(job["id"], "job.id")
    if "description" in job and not isinstance(job["description"], str):
        raise ValidationError("job.description must be a string")

    variables = _mapping(document.get("variables", {}), "variables")
    known_variables = set()
    for variable_name, value in variables.items():
        _name(variable_name, "variables key")
        if variable_name.lower() in _RESERVED_SECRET_NAMES or variable_name.lower().endswith(("_password", "_passwd", "_secret", "_credential")):
            raise ValidationError("secret-like variable names are not permitted")
        if "{{" in str(value) or "}}" in str(value):
            _check_reference(value, "variables." + variable_name, set(), known_variables)
        known_variables.add(variable_name)

    databases = _mapping(document["databases"], "databases")
    if not databases:
        raise ValidationError("databases must contain at least one database")
    provider_names = set()
    for database_id, raw_database in databases.items():
        _name(database_id, "database ID")
        database = _mapping(raw_database, "databases." + database_id)
        _keys(database, _DATABASE_KEYS, {"host", "database", "user", "credential"}, "databases." + database_id)
        for field in ("host", "database", "user"):
            if not isinstance(database[field], str) or not database[field]:
                raise ValidationError("databases.{}.{} must be a non-empty string".format(database_id, field))
        if "port" in database and (isinstance(database["port"], bool) or not isinstance(database["port"], int) or not 1 <= database["port"] <= 65535):
            raise ValidationError("databases.{}.port must be between 1 and 65535".format(database_id))
        if "connect_timeout" in database:
            _positive_number(database["connect_timeout"], "databases.{}.connect_timeout".format(database_id))
        session = _mapping(database.get("session", {}), "databases.{}.session".format(database_id))
        _keys(session, {"mode"}, set(), "databases.{}.session".format(database_id))
        if session.get("mode", (config or {}).get("session", {}).get("mode", "reuse")) not in {"reuse", "new"}:
            raise ValidationError("databases.{}.session.mode must be reuse or new".format(database_id))
        credential = _mapping(database["credential"], "databases.{}.credential".format(database_id))
        _keys(credential, {"provider", "options"}, {"provider"}, "databases.{}.credential".format(database_id))
        provider = credential["provider"]
        if not isinstance(provider, str) or not _PROVIDER.fullmatch(provider):
            raise ValidationError("databases.{}.credential.provider must be a provider name, not a path".format(database_id))
        provider_names.add(provider)
        _mapping(credential.get("options", {}), "databases.{}.credential.options".format(database_id))
        ssl = _mapping(database.get("ssl", {}), "databases.{}.ssl".format(database_id))
        _keys(ssl, {"mode", "ca_file"}, set(), "databases.{}.ssl".format(database_id))
        if ssl.get("mode", "verify-full") not in {"verify-full", "disable"}:
            raise ValidationError("databases.{}.ssl.mode must be verify-full or disable".format(database_id))
        if ssl.get("mode") == "disable" and config and not config["postgresql"].get("allow_insecure", False):
            raise ValidationError("databases.{}.ssl.mode disable requires application policy permission".format(database_id))
        if "ca_file" in ssl and not isinstance(ssl["ca_file"], str):
            raise ValidationError("databases.{}.ssl.ca_file must be a path string".format(database_id))

    if config is not None:
        provider_root = Path(config["provider_dir"]).resolve()
        for provider_name in provider_names:
            provider_file = (provider_root / (provider_name + ".py")).resolve()
            try:
                provider_file.relative_to(provider_root)
            except ValueError:
                raise ValidationError("provider resolves outside the approved provider directory") from None
            if not provider_file.is_file() or not os.access(str(provider_file), os.R_OK):
                raise ValidationError("approved provider is unavailable: {}".format(provider_name))

    steps = document["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValidationError("steps must be a non-empty ordered list")
    known_steps = set()
    sql_steps = set()
    root = Path(template_path).expanduser().resolve().parent

    def validate_step(raw_step, location, transaction_db=None):
        nonlocal known_variables
        step = _mapping(raw_step, location)
        step_type = step.get("type")
        if step_type == "sql":
            allowed, required = _SQL_KEYS, {"id", "type", "db"}
        elif step_type == "output":
            allowed, required = _OUTPUT_KEYS, {"id", "type", "source", "target", "format"}
        elif step_type == "transaction":
            allowed, required = _TRANSACTION_KEYS, {"id", "type", "db", "steps"}
        else:
            raise ValidationError("{}.type must be sql, output, or transaction".format(location))
        _keys(step, allowed, required, location)
        step_id = step["id"]
        _name(step_id, location + ".id")
        if step_id in known_steps:
            raise ValidationError("duplicate step ID: {}".format(step_id))
        known_steps.add(step_id)
        if "when" in step:
            _check_condition(step["when"], location + ".when", known_steps - {step_id}, known_variables)
        on_error = _mapping(step.get("on_error", {}), location + ".on_error")
        _keys(on_error, {"action", "retries"}, set(), location + ".on_error")
        if on_error.get("action", "fail") not in {"fail", "continue"}:
            raise ValidationError("{}.on_error.action must be fail or continue".format(location))
        if step_type == "transaction" and on_error.get("action", "fail") != "fail":
            raise ValidationError("transaction steps cannot continue after failure")
        retries = on_error.get("retries", 0)
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValidationError("{}.on_error.retries must be a non-negative integer".format(location))
        if retries:
            raise ValidationError("SQL retries are not supported in v1 because execution may be ambiguous")
        if transaction_db and on_error.get("action", "fail") != "fail":
            raise ValidationError("transaction child steps cannot continue after failure")

        if step_type == "sql":
            database_id = step["db"]
            if database_id not in databases:
                raise ValidationError("{}.db references an unknown database".format(location))
            if transaction_db and database_id != transaction_db:
                raise ValidationError("transaction child steps must use the parent database")
            if transaction_db and "session" in step:
                raise ValidationError("transaction children cannot override session mode")
            if ("sql" in step) == ("sql_file" in step):
                raise ValidationError("{} must specify exactly one of sql or sql_file".format(location))
            if "sql" in step and (not isinstance(step["sql"], str) or not step["sql"].strip()):
                raise ValidationError("{}.sql must be a non-empty string".format(location))
            if "sql_file" in step:
                step["_resolved_sql_file"] = str(_safe_sql_file(step["sql_file"], root, location + ".sql_file"))
            session = _mapping(step.get("session", {}), location + ".session")
            _keys(session, {"mode"}, set(), location + ".session")
            global_session_mode = (config or {}).get("session", {}).get("mode", "reuse")
            if session.get("mode", databases[database_id].get("session", {}).get("mode", global_session_mode)) not in {"reuse", "new"}:
                raise ValidationError("{}.session.mode must be reuse or new".format(location))
            if "timeout" in step:
                _positive_number(step["timeout"], location + ".timeout")
            params = _mapping(step.get("params", {}), location + ".params")
            for param_name, param_value in params.items():
                _name(param_name, location + ".params key")
                _check_reference(param_value, location + ".params." + param_name, known_steps - {step_id}, known_variables)
            result = _mapping(step.get("result", {"mode": "none"}), location + ".result")
            _keys(result, _RESULT_KEYS, set(), location + ".result")
            if result.get("mode", "none") not in {"none", "scalar", "first", "rows", "stream"}:
                raise ValidationError("{}.result.mode is unsupported".format(location))
            for cap_name in ("max_rows", "max_bytes"):
                if cap_name in result:
                    _positive_integer(result[cap_name], location + ".result." + cap_name)
            result_mode = result.get("mode", "none")
            if result_mode == "none" and "max_bytes" in result:
                raise ValidationError("{}.result.max_bytes does not apply to mode none".format(location))
            if result_mode in {"first", "scalar"} and "max_rows" in result:
                raise ValidationError("{}.result.max_rows does not apply to mode {}".format(location, result_mode))
            if result_mode == "stream" and ("max_rows" in result or "max_bytes" in result):
                raise ValidationError("stream limits use application results.max_output_bytes, not result.max_rows/max_bytes")
            if transaction_db and result.get("mode", "none") == "stream":
                raise ValidationError("stream results are not supported inside transaction groups")
            if result.get("mode", "none") == "stream" and session.get("mode", databases[database_id].get("session", {}).get("mode", global_session_mode)) == "new":
                raise ValidationError("stream results require a reusable database session")
            named = _mapping(step.get("set", {}), location + ".set")
            for variable_name, value in named.items():
                _name(variable_name, location + ".set key")
                if variable_name.lower() in _RESERVED_SECRET_NAMES or variable_name.lower().endswith(("_password", "_passwd", "_secret", "_credential")):
                    raise ValidationError("secret-like variable names are not permitted")
                _check_reference(value, location + ".set." + variable_name, known_steps, known_variables, current_id=step_id)
            known_variables.update(named)
            sql_steps.add(step_id)
        elif step_type == "output":
            if transaction_db:
                raise ValidationError("output steps cannot appear inside a transaction")
            source = step["source"]
            if not isinstance(source, str) or source not in sql_steps:
                raise ValidationError("{}.source must reference an earlier SQL step".format(location))
            if step["format"] not in {"text", "csv", "json", "jsonl"}:
                raise ValidationError("{}.format is unsupported".format(location))
            target = _mapping(step["target"], location + ".target")
            if "mode" in step and step["mode"] not in {"append", "overwrite"}:
                raise ValidationError("{}.mode must be append or overwrite".format(location))
            target_type = target.get("type")
            if target_type == "stdout":
                _keys(target, {"type"}, {"type"}, location + ".target")
                if "mode" in step:
                    raise ValidationError("output mode applies only to file targets")
            elif target_type == "file":
                _keys(target, {"type", "path"}, {"type", "path"}, location + ".target")
                output_path = target["path"]
                if not isinstance(output_path, str) or not Path(output_path).is_absolute():
                    raise ValidationError("{}.target.path must be an absolute path".format(location))
                if Path(output_path).exists() and (Path(output_path).is_symlink() or not Path(output_path).is_file()):
                    raise ValidationError("{}.target.path must be a regular file, not a symlink or special file".format(location))
                if not Path(output_path).parent.is_dir():
                    raise ValidationError("{}.target.path parent directory must exist".format(location))
                if step.get("mode", "append") not in {"append", "overwrite"}:
                    raise ValidationError("{}.mode must be append or overwrite".format(location))
            else:
                raise ValidationError("{}.target.type must be stdout or file".format(location))
            if step["format"] == "text":
                if "text" not in step or not isinstance(step["text"], str):
                    raise ValidationError("{}.text is required for text output".format(location))
                _check_reference(step["text"], location + ".text", known_steps, known_variables, mixed=True, allow_result=True)
            elif "text" in step:
                raise ValidationError("{}.text is only valid for text output".format(location))
        else:
            if transaction_db:
                raise ValidationError("nested transaction groups are not supported")
            database_id = step["db"]
            if database_id not in databases:
                raise ValidationError("{}.db references an unknown database".format(location))
            if databases[database_id].get("session", {}).get("mode", (config or {}).get("session", {}).get("mode", "reuse")) != "reuse":
                raise ValidationError("transaction groups require the database reusable session mode")
            children = step["steps"]
            if not isinstance(children, list) or not children:
                raise ValidationError("{}.steps must be a non-empty list".format(location))
            for index, child in enumerate(children, 1):
                validate_step(child, "{}.steps[{}]".format(location, index), transaction_db=database_id)

    for index, step in enumerate(steps, 1):
        validate_step(step, "steps[{}]".format(index))

    for index, step in enumerate(steps):
        if step.get("type") == "sql" and step.get("result", {}).get("mode", "none") == "stream":
            if index + 1 >= len(steps):
                raise ValidationError("stream result must be consumed by the immediately following output step")
            consumer = steps[index + 1]
            if consumer.get("type") != "output" or consumer.get("source") != step["id"] or consumer.get("format") not in {"csv", "jsonl"}:
                raise ValidationError("stream result requires an adjacent CSV or JSONL output step")
        if step.get("type") == "output":
            source = step.get("source")
            source_step = next((candidate for candidate in steps if candidate.get("id") == source), None)
            if source_step and source_step.get("result", {}).get("mode", "none") == "stream":
                if index == 0 or steps[index - 1].get("id") != source or step.get("format") not in {"csv", "jsonl"}:
                    raise ValidationError("stream output must immediately follow its SQL source and use CSV or JSONL")

    return document


def describe_template(document, config=None):
    """Return a secret-free plain-text execution summary."""
    lines = ["Job: {}".format(document["job"]["id"]), "", "Databases:"]
    for database_id, database in document["databases"].items():
        mode = database.get("session", {}).get("mode", (config or {}).get("session", {}).get("mode", "reuse"))
        provider = database["credential"]["provider"]
        lines.extend(["  {}".format(database_id), "    provider: {}".format(provider), "    session: {}".format(mode)])
    lines.extend(["", "Execution:"])

    def append_step(step, number):
        kind = step["type"].upper()
        location = step.get("db", "")
        suffix = " {}".format(location) if location else ""
        lines.append("  {}. {} {}{}".format(number, step["id"], kind, suffix))
        if kind == "TRANSACTION":
            for child_index, child in enumerate(step["steps"], 1):
                append_step(child, "{}.{}".format(number, child_index))

    for index, step in enumerate(document["steps"], 1):
        append_step(step, index)
    reusable = [key for key, db in document["databases"].items() if db.get("session", {}).get("mode", (config or {}).get("session", {}).get("mode", "reuse")) == "reuse"]
    lines.extend(["", "Reusable sessions:"])
    lines.extend(["  " + item for item in reusable] or ["  (none)"])
    lines.extend(["", "Validation: OK"])
    return "\n".join(lines)