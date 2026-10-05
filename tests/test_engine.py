import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path

from dbeeapp.engine import WorkflowEngine
from dbeeapp.errors import SQLError, TransactionError


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self.rows = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))
        if "FAIL" in sql:
            raise ValueError("secret driver detail")
        if sql.startswith("DECLARE"):
            sql = sql.split(" CURSOR FOR ", 1)[1]
        if sql.startswith("SELECT"):
            self.description = [("value",)]
            literal = re.search(r"SELECT\s+(\d+)", sql)
            value = params.get("input") if params else int(literal.group(1)) if literal else 42
            self.rows = [(value,)]
            self.rowcount = 1
        elif sql.startswith("FETCH"):
            self.description = [("value",)]
            if self.connection.stream_fetch_started:
                self.rows = []
            self.connection.stream_fetch_started = True
            self.rowcount = 0
        else:
            self.description = None
            self.rows = []
            self.rowcount = 1

    def fetchmany(self, size):
        result, self.rows = self.rows[:size], self.rows[size:]
        return result

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.executed = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.stream_fetch_started = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class FakeSessions:
    def __init__(self):
        self.connections = []
        self.closed = False
        self.reusable = {}

    @contextlib.contextmanager
    def session(self, database_id, mode="reuse"):
        if mode == "new":
            connection = FakeConnection()
        else:
            connection = self.reusable.get(database_id)
            if connection is None:
                connection = FakeConnection()
                self.reusable[database_id] = connection
        self.connections.append((database_id, mode, connection))
        yield connection

    def close_all(self):
        self.closed = True
        for connection in self.reusable.values():
            connection.close()


def config():
    return {
        "timeouts": {"sql": 0.0},
        "results": {"fetch_batch_size": 10, "max_rows": 100, "max_bytes": 10000, "max_output_bytes": 10000},
        "logging": {"enabled": False, "file": None, "level": "CRITICAL"},
        "failures": {"enabled": False, "file": None, "tag": "failure"},
    }


def database():
    return {"main": {"user": "reader", "credential": {"provider": "dummy"}}}


class WorkflowEngineTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.template_path = Path(self.tempdir.name) / "job.yaml"
        self.template_path.touch()
        self.sessions = FakeSessions()
        self.output = io.StringIO()

    def run_engine(self, steps, variables=None):
        document = {"job": {"id": "engine_test"}, "variables": variables or {}, "databases": database(), "steps": steps}
        engine = WorkflowEngine(document, self.template_path, config(), sessions=self.sessions, stdout=self.output)
        return engine.run(), engine

    def test_sql_parameters_and_explicit_variable_reuse(self):
        _, engine = self.run_engine([
            {"id": "lookup", "type": "sql", "db": "main", "sql": "SELECT :input", "params": {"input": "{{ vars.seed }}"}, "result": {"mode": "first"}, "set": {"value": "{{ steps.lookup.first.value }}"}},
            {"id": "second", "type": "sql", "db": "main", "sql": "SELECT :input", "params": {"input": "{{ vars.value }}"}, "result": {"mode": "scalar"}},
        ], variables={"seed": "bound-value"})
        connection = self.sessions.connections[0][2]
        executed_sql = [item for item in connection.executed if item[0].startswith("SELECT")]
        self.assertEqual(executed_sql[0][1], {"input": "bound-value"})
        self.assertEqual(executed_sql[1][1], {"input": "bound-value"})
        self.assertEqual(engine.context["steps"]["second"]["scalar"], "bound-value")
        self.assertEqual(connection.commits, 2)
        self.assertTrue(self.sessions.closed)

    def test_failed_step_rolls_back_and_does_not_log_driver_secret(self):
        with self.assertRaises(SQLError) as raised:
            self.run_engine([{"id": "broken", "type": "sql", "db": "main", "sql": "SELECT FAIL", "result": {"mode": "none"}}])
        self.assertNotIn("secret driver detail", str(raised.exception))
        self.assertEqual(self.sessions.connections[0][2].rollbacks, 1)
        self.assertTrue(self.sessions.closed)

    def test_transaction_failure_rolls_back_and_stops_children(self):
        transaction = {
            "id": "atomic",
            "type": "transaction",
            "db": "main",
            "steps": [
                {"id": "write_one", "type": "sql", "db": "main", "sql": "UPDATE t SET v = 1"},
                {"id": "fail", "type": "sql", "db": "main", "sql": "SELECT FAIL"},
                {"id": "never", "type": "sql", "db": "main", "sql": "UPDATE t SET v = 2"},
            ],
        }
        with self.assertRaises(TransactionError):
            self.run_engine([transaction])
        connection = self.sessions.connections[0][2]
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.commits, 0)
        self.assertNotIn("never", [entry[0] for entry in connection.executed])
        self.assertTrue(self.sessions.closed)

    def test_output_stdout_writes_result(self):
        self.run_engine([
            {"id": "lookup", "type": "sql", "db": "main", "sql": "SELECT 9", "result": {"mode": "first"}},
            {"id": "report", "type": "output", "source": "lookup", "target": {"type": "stdout"}, "format": "text", "text": "value={{ result }}"},
        ])
        self.assertEqual(self.output.getvalue(), 'value={"value":9}\n')

    def test_stream_is_drained_to_jsonl_before_session_cleanup(self):
        self.run_engine([
            {"id": "stream", "type": "sql", "db": "main", "sql": "SELECT generate_series", "result": {"mode": "stream"}},
            {"id": "write", "type": "output", "source": "stream", "target": {"type": "stdout"}, "format": "jsonl"},
        ])
        self.assertEqual(self.output.getvalue(), '{"value":42}\n')


if __name__ == "__main__":
    unittest.main()