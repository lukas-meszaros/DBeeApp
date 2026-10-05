import tempfile
import unittest
from pathlib import Path

from dbeeapp.errors import ValidationError
from dbeeapp.template_loader import load_yaml


class TemplateLoaderTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "job.yaml"

    def test_loads_standard_yaml_values(self):
        self.path.write_text("version: 1\nvalues: [one, two]\n", encoding="utf-8")
        self.assertEqual(load_yaml(self.path), {"version": 1, "values": ["one", "two"]})

    def test_rejects_duplicate_keys_at_any_depth(self):
        self.path.write_text("outer:\n  key: first\n  key: second\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "duplicate mapping key"):
            load_yaml(self.path)

    def test_rejects_python_object_tags(self):
        self.path.write_text("!!python/object/apply:os.system ['echo unsafe']\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            load_yaml(self.path)

    def test_rejects_multiple_documents(self):
        self.path.write_text("version: 1\n---\nversion: 1\n", encoding="utf-8")
        with self.assertRaises(ValidationError):
            load_yaml(self.path)

    def test_rejects_aliases(self):
        self.path.write_text("shared: &shared value\ncopy: *shared\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "YAML aliases are not supported"):
            load_yaml(self.path)

    def test_rejects_oversized_yaml(self):
        self.path.write_text("value: too much\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "byte limit"):
            load_yaml(self.path, max_bytes=4)


if __name__ == "__main__":
    unittest.main()