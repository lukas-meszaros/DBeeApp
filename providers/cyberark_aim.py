#!/usr/bin/env python3
"""CyberArk AIM Web Service provider; endpoint contract is deployment-configured."""

import json
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def main():
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or request.get("version") != 1:
            return 2
        username = request.get("username")
        options = request.get("options")
        if not isinstance(username, str) or not isinstance(options, dict):
            return 2
        base_url = options.get("base_url")
        app_id = options.get("app_id")
        safe = options.get("safe")
        folder = options.get("folder", "Root")
        account_parameter = options.get("account_parameter", "Object")
        ca_file = options.get("ca_file")
        timeout = options.get("timeout", 10)
        if not all(isinstance(value, str) and value for value in (base_url, app_id, safe, folder)):
            return 2
        if account_parameter not in {"Object", "UserName"}:
            return 2
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            return 2
        parts = urlsplit(base_url)
        if parts.scheme != "https" or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
            return 2
        api_url = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/") + "/AIMWebService/api/Accounts", "", ""))
        query = urlencode({"AppID": app_id, "Safe": safe, "Folder": folder, account_parameter: username})
        context = ssl.create_default_context(cafile=ca_file)
        http_request = Request(api_url + "?" + query, headers={"Accept": "application/json"})
        with urlopen(http_request, timeout=float(timeout), context=context) as response:
            response_body = response.read(1024 * 1024 + 1)
        if len(response_body) > 1024 * 1024:
            return 3
        payload = json.loads(response_body.decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("Content"), str):
            return 3
        json.dump({"version": 1, "password": payload["Content"]}, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
        return 0
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return 4


if __name__ == "__main__":
    raise SystemExit(main())