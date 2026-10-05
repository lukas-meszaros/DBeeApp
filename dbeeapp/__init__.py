"""DBeeApp declarative PostgreSQL workflow runner."""

from pathlib import Path
import sys

_VENDORED_LIBRARIES = Path(__file__).resolve().parent / "_vendor"
if not _VENDORED_LIBRARIES.is_dir():
	raise RuntimeError("DBeeApp local runtime libraries are missing: {}".format(_VENDORED_LIBRARIES))
sys.path.insert(0, str(_VENDORED_LIBRARIES))

__version__ = "0.1.0"