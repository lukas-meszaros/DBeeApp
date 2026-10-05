import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from dbeeapp.cli import main


TEMPLATE = """version: 1
job:
  id: safe_describe
databases:
  main:
    host: localhost
    database: sample
    user: reader
    credential:
      provider: dummy
      options:
        password: dummy-not-secret
steps:
  - id: inspect
    type: sql
    db: main
    sql: SELECT 1
"""


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "job.yaml"
        self.path.write_text(TEMPLATE, encoding="utf-8")

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_version(self):
        code, output, _ = self.invoke("version")
        self.assertEqual(code, 0)
        self.assertIn("DBeeApp 0.1.0", output)

    def test_validate_and_describe_do_not_show_password(self):
        code, output, _ = self.invoke("validate", str(self.path))
        self.assertEqual(code, 0)
        self.assertIn("Validation: OK", output)
        code, output, _ = self.invoke("describe", str(self.path))
        self.assertEqual(code, 0)
        self.assertIn("provider: dummy", output)
        self.assertNotIn("dummy-not-secret", output)

    def test_dry_run_is_explicitly_side_effect_free(self):
        code, output, _ = self.invoke("run", str(self.path), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("no providers, database connections, SQL, or outputs", output)
        self.assertIn("correctness and database-side safety were not tested", output)

    def test_validation_errors_use_documented_exit_code(self):
        self.path.write_text("version: 99\n", encoding="utf-8")
        code, _, stderr = self.invoke("validate", str(self.path))
        self.assertEqual(code, 3)
        self.assertIn("[validation]", stderr)


if __name__ == "__main__":
    unittest.main()