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

    def test_provider_defaults_are_read_from_yaml(self):
        self.path.write_text(
            "providers:\n  cyberark_aim:\n    base_url: https://aim.example.invalid\n    timeout: 8\n",
            encoding="utf-8",
        )
        config = load_config(self.path)
        self.assertEqual(config["providers"]["cyberark_aim"]["timeout"], 8)
        self.assertEqual(config["providers"]["cyberark_aim"]["base_url"], "https://aim.example.invalid")

    def test_provider_defaults_must_be_a_mapping(self):
        self.path.write_text("providers:\n  cyberark_aim: invalid\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigurationError, "providers.cyberark_aim must be a mapping"):
            load_config(self.path)

    def test_provider_names_must_be_safe_identifiers(self):
        self.path.write_text("providers:\n  ../cyberark: {}\n", encoding="utf-8")
        with self.assertRaisesRegex(ConfigurationError, "provider names must be lowercase identifiers"):
            load_config(self.path)

    def test_production_and_testbed_config_names_have_intended_content(self):
        config_dir = Path(__file__).resolve().parents[1] / "config"
        production = load_config(config_dir / "dbeeapp.yaml.example")
        testbed = load_config(config_dir / "dbeeapp.testbed.yaml")
        self.assertIn("cyberark_aim", production["providers"])
        self.assertEqual(production["postgresql"]["ssl_mode"], "verify-full")
        self.assertEqual(testbed["postgresql"]["ssl_mode"], "disable")
        self.assertTrue(testbed["postgresql"]["allow_insecure"])


if __name__ == "__main__":
    unittest.main()