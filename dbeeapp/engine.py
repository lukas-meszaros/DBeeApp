"""Sequential workflow execution with explicit connection and transaction ownership."""

import logging
import sys
import time
from pathlib import Path

from dbeeapp.conditions import evaluate_condition
from dbeeapp.errors import (
    ConnectionLostError,
    DBeeAppError,
    InternalError,
    SQLError,
    TransactionError,
)
from dbeeapp.database import commit, execute, execute_stream, rollback
from dbeeapp.outputs import write_output
from dbeeapp.resolver import resolve_value
from dbeeapp.results import collect_result
from dbeeapp.sessions import SessionManager
from dbeeapp.server_output import drain_notices, route_notices


def _logger(config, override_level=None):
    logger = logging.getLogger("dbeeapp")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(override_level or config["logging"]["level"])
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    if config["logging"]["enabled"]:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        logger.addHandler(stream)
    log_path = config["logging"].get("file")
    if config["logging"]["enabled"] and log_path:
        try:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            logger.warning("application log file could not be opened")
    return logger


class WorkflowEngine:
    """Run one validated template against injected sessions and output streams."""

    def __init__(self, document, template_path, config, sessions=None, stdout=None, logger=None):
        self.document = document
        self.template_path = Path(template_path).resolve()
        self.config = config
        self.sessions = sessions or SessionManager(document["databases"], config)
        self.stdout = stdout or sys.stdout
        self.logger = logger or _logger(config)
        self.context = {"vars": dict(document.get("variables", {})), "steps": {}}
        self.source_results = {}

    def run(self):
        try:
            for step in self.document["steps"]:
                self._run_step(step)
            return 0
        finally:
            self.sessions.close_all()

    def _run_step(self, step):
        started = time.monotonic()
        step_id = step["id"]
        if step.get("when") is not None and not evaluate_condition(step["when"], self.context):
            if step["type"] == "output":
                source = self.context["steps"].get(step.get("source"), {})
                stream = source.get("stream") if isinstance(source, dict) else None
                if stream is not None:
                    stream.close()
            self.context["steps"][step_id] = {"status": "skipped", "duration": 0.0}
            self.logger.info("job=%s step=%s status=skipped", self.document["job"]["id"], step_id)
            return
        try:
            if step["type"] == "sql":
                result = self._run_sql(step)
            elif step["type"] == "output":
                result = self._run_output(step)
            else:
                result = self._run_transaction(step)
            result.setdefault("status", "success")
            result["duration"] = time.monotonic() - started
            self.context["steps"][step_id] = result
            self.logger.info("job=%s step=%s database=%s status=success duration=%.3f", self.document["job"]["id"], step_id, step.get("db", "-"), result["duration"])
        except DBeeAppError as error:
            elapsed = time.monotonic() - started
            self.context["steps"][step_id] = {"status": "failure", "error_category": error.category, "duration": elapsed}
            self.logger.error("job=%s step=%s database=%s status=failure category=%s duration=%.3f", self.document["job"]["id"], step_id, step.get("db", "-"), error.category, elapsed)
            if self.config["failures"]["enabled"] and self.config["failures"].get("file"):
                self._log_failure(step_id, error.category)
            if step.get("on_error", {}).get("action", "fail") == "continue" and step["type"] != "transaction":
                return
            raise
        except Exception:
            self.context["steps"][step_id] = {"status": "failure", "error_category": "internal", "duration": time.monotonic() - started}
            self.logger.error("job=%s step=%s status=failure category=internal", self.document["job"]["id"], step_id)
            raise InternalError("workflow step failed unexpectedly") from None

    def _log_failure(self, step_id, category):
        path = self.config["failures"].get("file")
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write("{} job={} step={} category={}\n".format(self.config["failures"]["tag"], self.document["job"]["id"], step_id, category))
        except OSError:
            self.logger.warning("failure log could not be written")

    def _sql_text(self, step):
        if "sql" in step:
            return step["sql"]
        try:
            return Path(step["_resolved_sql_file"]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise SQLError("external SQL file could not be read") from None

    def _route_server_output(self, connection, step):
        notices, dropped = drain_notices(connection)
        route_notices(
            notices,
            dropped,
            self.config,
            self.stdout,
            self.logger,
            self.document["job"]["id"],
            step["id"],
            step["db"],
        )

    def _sql_on_connection(self, step, connection, in_transaction=False):
        started = time.monotonic()
        cursor = None
        streaming_cursor = None
        try:
            cursor = connection.cursor()
            params = {key: resolve_value(value, self.context) for key, value in step.get("params", {}).items()}
            timeout = float(step.get("timeout", self.config["timeouts"]["sql"]))
            mode = step.get("result", {}).get("mode", "none")
            sql = self._sql_text(step)
            if mode == "stream":
                streaming_cursor = execute_stream(
                    cursor,
                    sql,
                    params,
                    timeout,
                    self.config["results"]["fetch_batch_size"],
                    notice_callback=lambda: self._route_server_output(connection, step),
                )
                self._route_server_output(connection, step)
                result = collect_result(streaming_cursor, mode, self.config, step.get("result", {}))
            else:
                execute(cursor, sql, params, timeout)
                self._route_server_output(connection, step)
                result = collect_result(cursor, mode, self.config, step.get("result", {}))
            if mode == "stream":
                stream = result["stream"]

                def finalized_stream():
                    completed = False
                    try:
                        yield from stream
                        completed = True
                    except ConnectionLostError:
                        self.sessions.invalidate(step["db"])
                        raise
                    finally:
                        if not in_transaction:
                            try:
                                commit(connection) if completed else rollback(connection)
                            except ConnectionLostError:
                                self.sessions.invalidate(step["db"])
                                raise
                            except DBeeAppError:
                                raise
                            except Exception:
                                pass

                result["stream"] = finalized_stream()
            elif not in_transaction:
                commit(connection)
                self._route_server_output(connection, step)
            result["status"] = "success"
            result["duration"] = time.monotonic() - started
            self.context["steps"][step["id"]] = result
            for name, expression in step.get("set", {}).items():
                self.context["vars"][name] = resolve_value(expression, self.context)
            return result
        except DBeeAppError as error:
            try:
                self._route_server_output(connection, step)
            except Exception:
                pass
            self.context["steps"][step["id"]] = {
                "status": "failure",
                "error_category": error.category,
                "duration": time.monotonic() - started,
            }
            if not in_transaction:
                try:
                    rollback(connection)
                except ConnectionLostError:
                    self.sessions.invalidate(step["db"])
                except Exception:
                    pass
            raise
        except Exception:
            try:
                self._route_server_output(connection, step)
            except Exception:
                pass
            self.context["steps"][step["id"]] = {
                "status": "failure",
                "error_category": "sql",
                "duration": time.monotonic() - started,
            }
            if not in_transaction:
                try:
                    rollback(connection)
                except ConnectionLostError:
                    self.sessions.invalidate(step["db"])
                except Exception:
                    pass
            raise SQLError("SQL step failed") from None
        finally:
            if cursor is not None and streaming_cursor is None:
                try:
                    cursor.close()
                except Exception:
                    pass

    def _run_sql(self, step):
        database_id = step["db"]
        database = self.document["databases"][database_id]
        mode = step.get("session", {}).get("mode", database.get("session", {}).get("mode", self.config.get("session", {}).get("mode", "reuse")))
        with self.sessions.session(database_id, mode) as connection:
            return self._sql_on_connection(step, connection)

    def _run_output(self, step):
        result = self.source_results.get(step["source"])
        if result is None:
            result = self.context["steps"].get(step["source"])
        if result is None or result.get("status") != "success":
            raise SQLError("output source has no successful result")
        write_output(step, result, self.context, self.config, self.stdout)
        return {"source": step["source"]}

    def _run_transaction(self, step):
        database_id = step["db"]
        connection_context = self.sessions.session(database_id, "reuse")
        try:
            with connection_context as connection:
                try:
                    for child in step["steps"]:
                        if child.get("when") is not None and not evaluate_condition(child["when"], self.context):
                            self.context["steps"][child["id"]] = {"status": "skipped", "duration": 0.0}
                            continue
                        self._sql_on_connection(child, connection, in_transaction=True)
                    commit(connection)
                except Exception as error:
                    try:
                        rollback(connection)
                    except Exception:
                        pass
                    if isinstance(error, ConnectionLostError):
                        self.sessions.invalidate(database_id)
                    raise
        except DBeeAppError as error:
            raise TransactionError("transaction group failed ({})".format(error.category)) from None
        except Exception:
            raise TransactionError("transaction group failed") from None
        return {"status": "success", "children": [child["id"] for child in step["steps"]]}


def run_job(document, template_path, config, log_level=None):
    """Run one workflow and return its documented process exit code."""
    logger = _logger(config, override_level=log_level)
    engine = WorkflowEngine(document, template_path, config, logger=logger)
    try:
        return engine.run()
    except DBeeAppError as error:
        print("DBeeApp error [{}]: {}".format(error.category, error.public_message), file=sys.stderr)
        return error.exit_code
    except KeyboardInterrupt:
        print("DBeeApp interrupted", file=sys.stderr)
        return 130