import json
import tempfile
import unittest
from pathlib import Path

from dbeeapp.credentials import invoke_provider
from dbeeapp.errors import ProviderError, ProviderTimeoutError


class ProviderRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.provider_dir = Path(self.tempdir.name)

    def write_provider(self, name, source):
        (self.provider_dir / (name + ".py")).write_text(source, encoding="utf-8")

    def test_dummy_provider_returns_password_protocol(self):
        repo_dummy = Path(__file__).resolve().parents[1] / "providers" / "dummy.py"
        (self.provider_dir / "dummy.py").write_text(repo_dummy.read_text(encoding="utf-8"), encoding="utf-8")
        secret = "do-not-log-this"
        self.assertEqual(invoke_provider(self.provider_dir, "dummy", "test_user", {"password": secret}, 2), secret)

    def test_malformed_response_does_not_expose_output(self):
        self.write_provider("bad", "import sys\nsys.stdin.read()\nprint('secret garbage')\n")
        with self.assertRaisesRegex(ProviderError, "malformed protocol") as raised:
            invoke_provider(self.provider_dir, "bad", "user", {}, 2)
        self.assertNotIn("secret garbage", str(raised.exception))

    def test_nonzero_stderr_is_not_forwarded(self):
        self.write_provider("bad", "import sys\nsys.stdin.read()\nprint('secret diagnostic', file=sys.stderr)\nsys.exit(4)\n")
        with self.assertRaises(ProviderError) as raised:
            invoke_provider(self.provider_dir, "bad", "user", {}, 2)
        self.assertNotIn("secret diagnostic", str(raised.exception))

    def test_timeout_kills_provider(self):
        self.write_provider("slow", "import sys, time\nsys.stdin.read()\ntime.sleep(5)\n")
        with self.assertRaises(ProviderTimeoutError):
            invoke_provider(self.provider_dir, "slow", "user", {}, 0.1)

    def test_path_and_protocol_validation(self):
        with self.assertRaises(ProviderError):
            invoke_provider(self.provider_dir, "../escape", "user", {}, 1)
        self.write_provider("extra", "import json, sys\nsys.stdin.read()\nprint(json.dumps({'version': 1, 'password': 'x', 'other': 'y'}))\n")
        with self.assertRaisesRegex(ProviderError, "invalid protocol"):
            invoke_provider(self.provider_dir, "extra", "user", {}, 1)


if __name__ == "__main__":
    unittest.main()