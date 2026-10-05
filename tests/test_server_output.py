import tempfile
import unittest
from collections import deque
from io import StringIO
from pathlib import Path

from dbeeapp.database import NoticeBuffer
from dbeeapp.server_output import drain_notices, route_notices


class ServerOutputTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.log_path = Path(self.tempdir.name) / "server-output.log"

    def test_disabled_routes_nothing(self):
        class Logger:
            def warning(self, message):
                raise AssertionError(message)

        class Connection:
            notices = deque([{"S": "NOTICE", "V": "NOTICE", "M": "hidden"}])

        notices, dropped = drain_notices(Connection())
        route_notices(notices, dropped, {"server_output": {}}, None, Logger(), "job", "step", "db")
        self.assertEqual(list(self.log_path.parent.iterdir()), [])

    def test_routes_primary_message_to_stdout_and_file_without_detail(self):
        class Logger:
            def warning(self, message):
                raise AssertionError(message)

        class Connection:
            notices = deque([{
                "S": "NOTICE", "V": "NOTICE", "C": "00000",
                "M": "run 17 processed 10 rows", "D": "sensitive detail must not be forwarded",
                "H": "sensitive hint must not be forwarded",
            }])

        output = StringIO()
        settings = {"server_output": {"stdout": True, "file": str(self.log_path), "max_message_bytes": 4096}}
        notices, dropped = drain_notices(Connection())
        route_notices(notices, dropped, settings, output, Logger(), "reference_job", "call_proc", "reporting")
        stdout_text = output.getvalue()
        file_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("NOTICE", stdout_text)
        self.assertIn("run 17 processed 10 rows", stdout_text)
        self.assertNotIn("sensitive detail", stdout_text)
        self.assertNotIn("sensitive hint", stdout_text)
        self.assertEqual(file_text, stdout_text)

    def test_message_is_truncated_at_configured_byte_limit(self):
        class Logger:
            def warning(self, message):
                raise AssertionError(message)

        output = StringIO()
        route_notices(
            [{"V": "NOTICE", "M": "x" * 100}], 0,
            {"server_output": {"stdout": True, "file": None, "max_message_bytes": 24}},
            output, Logger(), "job", "step", "db",
        )
        self.assertIn("[message truncated]", output.getvalue())

    def test_decodes_pg8000_bytes_fields(self):
        output = StringIO()
        route_notices(
            [{b"V": b"NOTICE", b"M": "procédure completed".encode("utf-8"), b"D": b"private detail"}],
            0,
            {"server_output": {"stdout": True, "file": None, "max_message_bytes": 100}},
            output,
            type("Logger", (), {"warning": lambda self, message: None})(),
            "job", "call", "db",
        )
        self.assertIn("NOTICE", output.getvalue())
        self.assertIn("procédure completed", output.getvalue())
        self.assertNotIn("private detail", output.getvalue())

    def test_overflow_is_reported(self):
        notices = NoticeBuffer(maxlen=1)
        notices.append({"V": "NOTICE", "M": "old"})
        notices.append({"V": "NOTICE", "M": "latest"})
        queued, dropped = drain_notices(type("Connection", (), {"notices": notices})())
        output = StringIO()
        logger = type("Logger", (), {"warning": lambda self, message: None})()
        route_notices(
            queued, dropped,
            {"server_output": {"stdout": True, "file": None, "max_message_bytes": 100}},
            output, logger, "job", "step", "db",
        )
        self.assertNotIn("old", output.getvalue())
        self.assertIn("latest", output.getvalue())
        self.assertIn("1 server messages omitted", output.getvalue())


if __name__ == "__main__":
    unittest.main()
