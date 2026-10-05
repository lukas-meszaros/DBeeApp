"""Bounded row conversion and DB-API result extraction."""

import datetime
import decimal
import json

import pg8000.dbapi

from dbeeapp.database import raise_database_error
from dbeeapp.errors import SQLError


def json_default(value):
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    raise TypeError("unsupported JSON value")


def row_mapping(columns, row):
    return {name: value for name, value in zip(columns, row)}


def _check_row_size(row, max_bytes):
    size = len(json.dumps(row, default=json_default, separators=(",", ":")).encode("utf-8"))
    if size > max_bytes:
        raise SQLError("query result exceeds configured byte limit")


def collect_result(cursor, mode, config, step_result=None):
    """Collect bounded results or return a batch iterator for streaming output."""
    columns = [description[0] for description in cursor.description or ()]
    result = {"columns": columns}
    if cursor.description is None:
        if mode == "scalar":
            raise SQLError("scalar result requires one column and at most one row")
        if mode == "stream":
            raise SQLError("stream result requires a query that returns rows")
        result["row_count"] = max(0, cursor.rowcount) if cursor.rowcount >= 0 else None
        if mode == "first":
            result["first"] = None
        elif mode == "rows":
            result["rows"] = []
        return result
    if mode == "stream":
        batch_size = config["results"]["fetch_batch_size"]

        def batches():
            try:
                while True:
                    try:
                        rows = cursor.fetchmany(batch_size)
                    except pg8000.dbapi.Error as error:
                        raise_database_error(error)
                    if not rows:
                        break
                    for row in rows:
                        yield row_mapping(columns, row)
            finally:
                close = getattr(cursor, "close", None)
                if close:
                    try:
                        close()
                    except Exception:
                        pass

        result["stream"] = batches()
        result["row_count"] = None
        return result

    step_result = step_result or {}
    max_rows = step_result.get("max_rows", config["results"]["max_rows"])
    max_bytes = step_result.get("max_bytes", config["results"]["max_bytes"])
    if mode == "none":
        count = 0
        while True:
            rows = cursor.fetchmany(config["results"]["fetch_batch_size"])
            if not rows:
                break
            count += len(rows)
            if count > max_rows:
                raise SQLError("query result exceeds configured row limit")
        result["row_count"] = count
        return result

    if mode == "first":
        rows = cursor.fetchmany(1)
        result["row_count"] = len(rows)
        result["first"] = row_mapping(columns, rows[0]) if rows else None
        if rows:
            _check_row_size(result["first"], max_bytes)
        return result
    if mode == "scalar":
        if len(columns) != 1:
            raise SQLError("scalar result requires exactly one column")
        rows = cursor.fetchmany(2)
        if len(rows) > 1:
            raise SQLError("scalar result requires at most one row")
        result["row_count"] = len(rows)
        result["scalar"] = rows[0][0] if rows else None
        if rows:
            _check_row_size({columns[0]: result["scalar"]}, max_bytes)
        return result

    retained = []
    total_bytes = 0
    while True:
        try:
            rows = cursor.fetchmany(min(config["results"]["fetch_batch_size"], max_rows + 1 - len(retained)))
        except pg8000.dbapi.Error as error:
            raise_database_error(error)
        if not rows:
            break
        for row in rows:
            mapped = row_mapping(columns, row)
            total_bytes += len(json.dumps(mapped, default=json_default, separators=(",", ":")).encode("utf-8"))
            if len(retained) >= max_rows or total_bytes > max_bytes:
                raise SQLError("query result exceeds configured safety limit")
            retained.append(mapped)
    result["row_count"] = len(retained)
    if mode == "rows":
        result["rows"] = retained
    return result