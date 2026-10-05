import tempfile
import unittest
from pathlib import Path

from dbeeapp.config import load_config
from dbeeapp.errors import ConfigurationError


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "config.yaml"

    def test_defaults_are_independent(self):
        first = load_config()
        first["timeouts"]["connect"] = 1
        self.assertEqual(load_config()["timeouts"]["connect"], 10.0)

    def test_loads_override_and_rejects_unknown_field(self):
        self.path.write_text("timeouts:\n  connect: 5\n", encoding="utf-8")
        self.assertEqual(load_config(self.path)["timeouts"]["connect"], 5)
        self.path.write_text("unexpected: true\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigurationError, "unknown field"):
            load_config(self.path)

    def test_disabling_tls_requires_explicit_admin_policy(self):
        self.path.write_text("postgresql:\n  ssl_mode: disable\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigurationError, "requires postgresql.allow_insecure"):
            load_config(self.path)

    def test_global_session_default_is_validated(self):
        self.path.write_text("session:\n  mode: new\n", encoding="utf-8")
        self.assertEqual(load_config(self.path)["session"]["mode"], "new")
        self.path.write_text("session:\n  mode: pool\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigurationError, "session.mode must be reuse or new"):
            load_config(self.path)


if __name__ == "__main__":
    unittest.main()