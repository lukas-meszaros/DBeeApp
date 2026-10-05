import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from dbeeapp.errors import OutputError
from dbeeapp.outputs import write_output


def make_config(max_output_bytes=10000):
    return {"results": {"max_output_bytes": max_output_bytes}}


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.output_path = Path(self.tempdir.name) / "output.txt"

    def test_csv_rows_and_header(self):
        stdout = io.StringIO()
        write_output(
            {"format": "csv", "target": {"type": "stdout"}},
            {"columns": ["id", "name"], "rows": [{"id": 1, "name": "alpha"}]},
            {"vars": {}, "steps": {}}, make_config(), stdout,
        )
        self.assertEqual(stdout.getvalue(), "id,name\n1,alpha\n")

    def test_jsonl_stream_is_batched_and_closes_source(self):
        class Rows:
            def __init__(self):
                self.closed = False

            def __iter__(self):
                yield {"id": 1}
                yield {"id": 2}

            def close(self):
                self.closed = True

        rows = Rows()
        stdout = io.StringIO()
        write_output(
            {"format": "jsonl", "target": {"type": "stdout"}},
            {"columns": ["id"], "stream": rows},
            {"vars": {}, "steps": {}}, make_config(), stdout,
        )
        self.assertEqual(stdout.getvalue(), '{"id":1}\n{"id":2}\n')
        self.assertTrue(rows.closed)

    def test_overwrite_is_atomic_and_enforces_limit(self):
        self.output_path.write_text("old", encoding="utf-8")
        step = {"format": "json", "target": {"type": "file", "path": str(self.output_path)}, "mode": "overwrite"}
        with self.assertRaises(OutputError):
            write_output(step, {"rows": [{"value": "too long"}]}, {"vars": {}, "steps": {}}, make_config(2), io.StringIO())
        self.assertEqual(self.output_path.read_text(encoding="utf-8"), "old")
        self.assertEqual(list(Path(self.tempdir.name).glob(".dbeeapp-*")), [])

    def test_json_output_is_parseable(self):
        stdout = io.StringIO()
        write_output(
            {"format": "json", "target": {"type": "stdout"}},
            {"rows": [{"id": 4}]}, {"vars": {}, "steps": {}}, make_config(), stdout,
        )
        self.assertEqual(json.loads(stdout.getvalue()), {"rows": [{"id": 4}]})


if __name__ == "__main__":
    unittest.main()