import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LocalRuntimeLibraryTests(unittest.TestCase):
    def run_isolated(self, code):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [sys.executable, "-S", "-c", code],
            cwd=str(ROOT),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def test_runtime_imports_resolve_from_repository_vendor_tree_without_site(self):
        result = self.run_isolated(
            "import dbeeapp, yaml, pg8000, scramp, asn1crypto, dateutil, six; "
            "from importlib.metadata import version; "
            "assert version('scramp') == '1.4.6'; "
            "print(yaml.__file__); print(pg8000.__file__); print(scramp.__file__); "
            "print(asn1crypto.__file__); print(dateutil.__file__); print(six.__file__)"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for line in result.stdout.splitlines():
            self.assertIn(str(ROOT / "dbeeapp" / "_vendor"), line)

    def test_cli_runs_with_site_packages_disabled(self):
        result = self.run_isolated("from dbeeapp.cli import main; raise SystemExit(main(['version']))")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DBeeApp 0.1.0", result.stdout)

    def test_vendored_tree_contains_no_native_extensions_and_keeps_licenses(self):
        vendor = ROOT / "dbeeapp" / "_vendor"
        native_files = [path for path in vendor.rglob("*") if path.suffix in {".so", ".pyd", ".dylib"}]
        license_files = list((vendor / "licenses").glob("*.txt"))
        self.assertEqual(native_files, [])
        self.assertEqual(len(license_files), 6)


if __name__ == "__main__":
    unittest.main()
