import contextlib
import io
import os
import unittest
from pathlib import Path

import dbeeapp
from dbeeapp.config import load_config
from dbeeapp.engine import WorkflowEngine
from dbeeapp.errors import TransactionError
from dbeeapp.sessions import SessionManager
from dbeeapp.template_loader import load_yaml
from dbeeapp.validator import validate_template
import pg8000.dbapi


ROOT = Path(__file__).resolve().parents[1]
ENABLED = os.environ.get("DBEEAPP_INTEGRATION") == "1"


@unittest.skipUnless(ENABLED, "set DBEEAPP_INTEGRATION=1 with testbed services running")
class PostgreSQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(ROOT / "config" / "dbeeapp.testbed.yaml")
        cls.control = {
            "host": "127.0.0.1", "port": 55432, "database": "control", "user": "control_user",
            "ssl": {"mode": "disable"},
            "credential": {"provider": "dummy", "options": {"password": "dbeeapp_control_test_only"}},
        }
        cls.reporting = {
            "host": "127.0.0.1", "port": 55433, "database": "reporting", "user": "reporting_user",
            "ssl": {"mode": "disable"},
            "credential": {"provider": "dummy", "options": {"password": "dbeeapp_reporting_test_only"}},
        }
        connection = pg8000.dbapi.connect(
            user="postgres", password="dbeeapp_control_admin_test_only", host="127.0.0.1",
            port=55432, database="control", ssl_context=False, timeout=5,
        )
        cursor = connection.cursor()
        cursor.execute("UPDATE control.account SET balance = CASE account_id WHEN 1 THEN 100 WHEN 2 THEN 50 END")
        cursor.execute("TRUNCATE control.audit_log RESTART IDENTITY")
        connection.commit()
        cursor.close()
        connection.close()

    def test_reuse_switch_new_override_and_temp_state(self):
        manager = SessionManager({"control": self.control, "reporting": self.reporting}, self.config)
        try:
            with manager.session("control") as control_first:
                cursor = control_first.cursor()
                cursor.execute("SELECT pg_backend_pid()")
                control_pid = cursor.fetchone()[0]
                cursor.execute("CREATE TEMP TABLE dbeeapp_session_test (value integer)")
                control_first.commit()
                cursor.close()
            with manager.session("reporting") as reporting:
                cursor = reporting.cursor()
                cursor.execute("SELECT pg_backend_pid()")
                reporting_pid = cursor.fetchone()[0]
                reporting.commit()
                cursor.close()
            with manager.session("control") as control_again:
                cursor = control_again.cursor()
                cursor.execute("SELECT pg_backend_pid()")
                self.assertEqual(cursor.fetchone()[0], control_pid)
                cursor.execute("INSERT INTO dbeeapp_session_test VALUES (1)")
                control_again.commit()
                cursor.close()
            with manager.session("control", "new") as isolated:
                cursor = isolated.cursor()
                cursor.execute("SELECT pg_backend_pid()")
                self.assertNotEqual(cursor.fetchone()[0], control_pid)
                with self.assertRaises(Exception):
                    cursor.execute("SELECT * FROM dbeeapp_session_test")
                isolated.rollback()
                cursor.close()
            with manager.session("control") as resumed:
                cursor = resumed.cursor()
                cursor.execute("SELECT pg_backend_pid(), (SELECT count(*) FROM dbeeapp_session_test)")
                resumed_pid, count = cursor.fetchone()
                self.assertEqual(resumed_pid, control_pid)
                self.assertEqual(count, 1)
                cursor.close()
            self.assertNotEqual(control_pid, reporting_pid)
        finally:
            manager.close_all()

    def test_example_templates_execute_end_to_end(self):
        example_names = (
            "basic_query", "cross_database", "external_sql", "conditional",
            "transaction_commit", "session_state", "session_override", "large_result_stream",
            "many_sequential_steps",
        )
        for example_name in example_names:
            with self.subTest(example=example_name):
                path = ROOT / "examples" / example_name / "job.yaml"
                document = validate_template(load_yaml(path), path, config=self.config)
                output = io.StringIO()
                engine = WorkflowEngine(document, path, self.config, stdout=output)
                self.assertEqual(engine.run(), 0)
                if example_name == "session_override.yaml":
                    self.assertEqual(engine.context["vars"]["reusable_pid"], engine.context["vars"]["resumed_pid"])
                    self.assertNotEqual(engine.context["vars"]["reusable_pid"], engine.context["vars"]["isolated_pid"])

    def test_transaction_children_share_exact_backend_session(self):
        document = {
            "job": {"id": "transaction_identity"},
            "databases": {"control": self.control},
            "steps": [{
                "id": "identity_group", "type": "transaction", "db": "control",
                "steps": [
                    {"id": "pid_first", "type": "sql", "db": "control", "sql": "SELECT pg_backend_pid() AS pid", "result": {"mode": "scalar"}},
                    {"id": "pid_second", "type": "sql", "db": "control", "sql": "SELECT pg_backend_pid() AS pid", "result": {"mode": "scalar"}},
                ],
            }],
        }
        engine = WorkflowEngine(document, ROOT / "examples" / "basic_query" / "job.yaml", self.config, stdout=io.StringIO())
        self.assertEqual(engine.run(), 0)
        self.assertEqual(engine.context["steps"]["pid_first"]["scalar"], engine.context["steps"]["pid_second"]["scalar"])
        self.assertEqual(engine.sessions.reusable, {})

    def test_transaction_failure_rolls_back_and_stops_children(self):
        manager = SessionManager({"control": self.control}, self.config)
        try:
            with manager.session("control") as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT account_id, balance FROM control.account ORDER BY account_id")
                before = cursor.fetchall()
                connection.commit()
                cursor.close()
        finally:
            manager.close_all()
        path = ROOT / "examples" / "transaction_rollback" / "job.yaml"
        document = validate_template(load_yaml(path), path, config=self.config)
        engine = WorkflowEngine(document, path, self.config, stdout=io.StringIO())
        with self.assertRaises(TransactionError):
            engine.run()
        self.assertEqual(engine.sessions.reusable, {})
        manager = SessionManager({"control": self.control}, self.config)
        try:
            with manager.session("control") as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT account_id, balance FROM control.account ORDER BY account_id")
                self.assertEqual(cursor.fetchall(), before)
                cursor.close()
        finally:
            manager.close_all()

    def test_statement_timeout_is_classified_and_session_recovers(self):
        document = {
            "job": {"id": "timeout_test"},
            "databases": {"control": self.control},
            "steps": [
                {
                    "id": "slow", "type": "sql", "db": "control", "sql": "SELECT pg_sleep(0.2)",
                    "timeout": 0.02, "on_error": {"action": "continue"},
                },
                {"id": "after_timeout", "type": "sql", "db": "control", "sql": "SELECT 1 AS value", "result": {"mode": "scalar"}},
            ],
        }
        engine = WorkflowEngine(document, ROOT / "examples" / "basic_query" / "job.yaml", self.config, stdout=io.StringIO())
        self.assertEqual(engine.run(), 0)
        self.assertEqual(engine.context["steps"]["slow"]["error_category"], "sql_timeout")
        self.assertEqual(engine.context["steps"]["after_timeout"]["scalar"], 1)


if __name__ == "__main__":
    unittest.main()