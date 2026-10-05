import tempfile
import unittest
from pathlib import Path

from dbeeapp.errors import ValidationError
from dbeeapp.validator import describe_template, validate_template


def base_template():
    return {
        "version": 1,
        "job": {"id": "sample"},
        "variables": {"customer_id": 17},
        "databases": {
            "main": {
                "host": "localhost",
                "database": "sample",
                "user": "reader",
                "credential": {"provider": "dummy", "options": {"password": "test-only"}},
            }
        },
        "steps": [
            {
                "id": "lookup",
                "type": "sql",
                "db": "main",
                "sql": "SELECT customer_id FROM customer WHERE customer_id = :customer_id",
                "params": {"customer_id": "{{ vars.customer_id }}"},
                "result": {"mode": "first"},
            }
        ],
    }


class TemplateValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "job.yaml"
        self.path.touch()

    def validate(self, template):
        return validate_template(template, self.path)

    def test_accepts_minimal_valid_template(self):
        template = base_template()
        self.assertIs(self.validate(template), template)

    def test_rejects_unsupported_version(self):
        template = base_template()
        template["version"] = 2
        with self.assertRaisesRegex(ValidationError, "unsupported template version"):
            self.validate(template)

    def test_rejects_unknown_properties(self):
        template = base_template()
        template["ignored"] = True
        with self.assertRaisesRegex(ValidationError, "unknown field"):
            self.validate(template)

    def test_rejects_duplicate_step_ids(self):
        template = base_template()
        template["steps"].append(dict(template["steps"][0]))
        with self.assertRaisesRegex(ValidationError, "duplicate step ID"):
            self.validate(template)

    def test_rejects_unknown_database(self):
        template = base_template()
        template["steps"][0]["db"] = "missing"
        with self.assertRaisesRegex(ValidationError, "unknown database"):
            self.validate(template)

    def test_rejects_undefined_variable(self):
        template = base_template()
        template["steps"][0]["params"]["customer_id"] = "{{ vars.missing }}"
        with self.assertRaisesRegex(ValidationError, "undefined workflow variable"):
            self.validate(template)

    def test_rejects_sql_retries(self):
        template = base_template()
        template["steps"][0]["on_error"] = {"retries": 1}
        with self.assertRaisesRegex(ValidationError, "SQL retries are not supported"):
            self.validate(template)

    def test_rejects_arbitrary_provider_paths(self):
        template = base_template()
        template["databases"]["main"]["credential"]["provider"] = "../external.py"
        with self.assertRaisesRegex(ValidationError, "provider name"):
            self.validate(template)

    def test_describe_does_not_show_credentials(self):
        text = describe_template(self.validate(base_template()))
        self.assertIn("provider: dummy", text)
        self.assertNotIn("test-only", text)

    def test_rejects_transaction_session_override(self):
        template = base_template()
        template["steps"] = [{
            "id": "tx",
            "type": "transaction",
            "db": "main",
            "steps": [{
                "id": "child", "type": "sql", "db": "main", "session": {"mode": "new"},
                "sql": "SELECT 1",
            }],
        }]
        with self.assertRaisesRegex(ValidationError, "cannot override session"):
            self.validate(template)

    def test_rejects_transactions_on_new_default_session(self):
        template = base_template()
        template["databases"]["main"]["session"] = {"mode": "new"}
        template["steps"] = [{
            "id": "tx", "type": "transaction", "db": "main",
            "steps": [{"id": "child", "type": "sql", "db": "main", "sql": "SELECT 1"}],
        }]
        with self.assertRaisesRegex(ValidationError, "require the database reusable"):
            self.validate(template)

    def test_stream_requires_adjacent_streaming_output(self):
        template = base_template()
        template["steps"][0]["result"] = {"mode": "stream"}
        with self.assertRaisesRegex(ValidationError, "immediately following output"):
            self.validate(template)

    def test_result_cap_fields_must_apply_to_selected_mode(self):
        template = base_template()
        template["steps"][0]["result"] = {"mode": "none", "max_bytes": 100}
        with self.assertRaisesRegex(ValidationError, "max_bytes does not apply to mode none"):
            self.validate(template)
        template["steps"][0]["result"] = {"mode": "stream", "max_rows": 10}
        template["steps"].append({
            "id": "write", "type": "output", "source": "lookup", "target": {"type": "stdout"}, "format": "jsonl",
        })
        with self.assertRaisesRegex(ValidationError, "stream limits use application"):
            self.validate(template)

    def test_stream_accepts_adjacent_jsonl_output(self):
        template = base_template()
        template["steps"][0]["result"] = {"mode": "stream"}
        template["steps"].append({
            "id": "write", "type": "output", "source": "lookup", "target": {"type": "stdout"}, "format": "jsonl",
        })
        self.assertIs(self.validate(template), template)

    def test_output_result_placeholder_is_supported(self):
        template = base_template()
        template["steps"].append({
            "id": "report", "type": "output", "source": "lookup", "target": {"type": "stdout"},
            "format": "text", "text": "{{ result }}",
        })
        self.assertIs(self.validate(template), template)

    def test_config_validation_checks_approved_provider_is_installed(self):
        template = base_template()
        config = {"provider_dir": str(Path(self.tempdir.name) / "providers"), "postgresql": {"allow_insecure": False}}
        with self.assertRaisesRegex(ValidationError, "approved provider is unavailable"):
            validate_template(template, self.path, config=config)

    def test_secret_like_workflow_variable_names_are_rejected(self):
        template = base_template()
        template["variables"]["db_password"] = "unsafe"
        with self.assertRaisesRegex(ValidationError, "secret-like variable names"):
            self.validate(template)

    def test_global_session_default_is_used_by_describe(self):
        template = base_template()
        config = {"provider_dir": str(Path(__file__).resolve().parents[1] / "providers"), "session": {"mode": "new"}, "postgresql": {"allow_insecure": False}}
        validate_template(template, self.path, config=config)
        self.assertIn("session: new", describe_template(template, config))

    def test_rejects_sql_file_path_traversal(self):
        template = base_template()
        template["steps"][0].pop("sql")
        template["steps"][0]["sql_file"] = "../outside.sql"
        with self.assertRaisesRegex(ValidationError, "escapes the template directory"):
            self.validate(template)


if __name__ == "__main__":
    unittest.main()