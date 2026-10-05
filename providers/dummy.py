#!/usr/bin/env python3
"""Development/test-only DBeeApp credential provider."""

import json
import sys


def main():
    request = json.load(sys.stdin)
    if not isinstance(request, dict) or request.get("version") != 1:
        return 2
    username = request.get("username")
    options = request.get("options")
    if not isinstance(username, str) or not isinstance(options, dict):
        return 2
    password = options.get("password")
    if not isinstance(password, str) or not password:
        return 2
    json.dump({"version": 1, "password": password}, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())