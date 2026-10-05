"""Administrator-approved password-provider subprocess boundary."""

import json
import os
import re
import selectors
import subprocess
import sys
import time
from pathlib import Path

from dbeeapp.errors import ProviderError, ProviderTimeoutError

_PROVIDER_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_MAX_REQUEST_BYTES = 32768
_MAX_RESPONSE_BYTES = 65536
_MAX_STDERR_BYTES = 8192


def _safe_provider_file(provider_dir, name):
    if not isinstance(name, str) or not _PROVIDER_NAME.fullmatch(name):
        raise ProviderError("provider name is invalid")
    root = Path(provider_dir).resolve()
    candidate = (root / (name + ".py")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise ProviderError("provider is not approved") from None
    if not candidate.is_file():
        raise ProviderError("approved provider is unavailable: {}".format(name))
    return candidate


def _terminate(process):
    if process.poll() is None:
        process.kill()
    process.wait()


def invoke_provider(provider_dir, name, username, options, timeout):
    """Invoke one fixed provider script with a bounded JSON stdin/stdout protocol."""
    script = _safe_provider_file(provider_dir, name)
    request = json.dumps(
        {"version": 1, "username": username, "options": options},
        separators=(",", ":"),
    ).encode("utf-8")
    if len(request) > _MAX_REQUEST_BYTES:
        raise ProviderError("provider request exceeds the size limit")
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    try:
        process = subprocess.Popen(
            [sys.executable, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            env=environment,
        )
    except OSError:
        raise ProviderError("provider could not be started: {}".format(name)) from None

    selector = selectors.DefaultSelector()
    stdout_data = bytearray()
    stderr_seen = 0
    request_offset = 0
    streams = {"stdin": process.stdin, "stdout": process.stdout, "stderr": process.stderr}
    for stream in streams.values():
        os.set_blocking(stream.fileno(), False)
    selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map() or process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _terminate(process)
                raise ProviderTimeoutError("provider timed out: {}".format(name))
            for key, _ in selector.select(min(remaining, 0.25)):
                stream = key.fileobj
                channel = key.data
                if channel == "stdin":
                    try:
                        written = os.write(stream.fileno(), request[request_offset:request_offset + 4096])
                    except BrokenPipeError:
                        written = 0
                    request_offset += written
                    if written == 0 or request_offset >= len(request):
                        selector.unregister(stream)
                        stream.close()
                else:
                    chunk = os.read(stream.fileno(), 4096)
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                    elif channel == "stdout":
                        stdout_data.extend(chunk)
                        if len(stdout_data) > _MAX_RESPONSE_BYTES:
                            _terminate(process)
                            raise ProviderError("provider response exceeds the size limit")
                    else:
                        stderr_seen = min(_MAX_STDERR_BYTES, stderr_seen + len(chunk))
        return_code = process.wait()
    except (KeyboardInterrupt, ProviderError):
        _terminate(process)
        raise
    finally:
        selector.close()
        for stream in streams.values():
            try:
                stream.close()
            except OSError:
                pass

    if return_code != 0:
        raise ProviderError("provider failed: {} (exit {})".format(name, return_code))
    try:
        response = json.loads(stdout_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderError("provider returned malformed protocol data: {}".format(name)) from None
    if not isinstance(response, dict) or set(response) != {"version", "password"}:
        raise ProviderError("provider returned an invalid protocol response: {}".format(name))
    if response["version"] != 1 or isinstance(response["version"], bool):
        raise ProviderError("provider returned an unsupported protocol version: {}".format(name))
    password = response["password"]
    if not isinstance(password, str) or not password:
        raise ProviderError("provider returned an invalid password value: {}".format(name))
    return password