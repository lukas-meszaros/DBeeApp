"""Bounded text, CSV, JSON, and JSONL output targets."""

import csv
import io
import json
import os
import tempfile
from pathlib import Path

from dbeeapp.errors import DBeeAppError, OutputError
from dbeeapp.resolver import render_text
from dbeeapp.results import json_default


def _encode(format_name, step, source_result, context):
    if format_name == "text":
        payload = render_text(step["text"], context, source_result.get("first", source_result.get("rows", source_result.get("scalar"))))
        return payload.encode("utf-8") + b"\n"
    if format_name == "json":
        return (json.dumps(source_result, default=json_default, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if format_name == "jsonl":
        rows = source_result.get("stream")
        if rows is None:
            rows = source_result.get("rows")
            if rows is None:
                rows = [source_result["first"]] if source_result.get("first") is not None else []

        def jsonl_lines():
            try:
                for row in rows:
                    line = json.dumps(row, default=json_default, ensure_ascii=False, separators=(",", ":")) + "\n"
                    yield line.encode("utf-8")
            finally:
                close = getattr(rows, "close", None)
                if close:
                    close()

        return jsonl_lines()
    if format_name == "csv":
        columns = source_result.get("columns", [])

        def csv_lines():
            rows = source_result.get("stream")
            if rows is None:
                rows = source_result.get("rows")
                if rows is None:
                    rows = [source_result["first"]] if source_result.get("first") is not None else []
            try:
                output = io.StringIO(newline="")
                csv.writer(output, lineterminator="\n").writerow(columns)
                yield output.getvalue().encode("utf-8")
                for row in rows:
                    output = io.StringIO(newline="")
                    csv.writer(output, lineterminator="\n").writerow([row.get(column) for column in columns])
                    yield output.getvalue().encode("utf-8")
            finally:
                close = getattr(rows, "close", None)
                if close:
                    close()

        return csv_lines()
    raise OutputError("unsupported output format")


def _chunks(payload):
    return payload if not isinstance(payload, bytes) else (payload,)


def _write_file(path, mode, payload, max_bytes):
    destination = Path(path)
    count = 0
    if mode == "overwrite":
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=str(destination.parent), prefix=".dbeeapp-", delete=False) as handle:
                temporary_path = handle.name
                for chunk in _chunks(payload):
                    count += len(chunk)
                    if count > max_bytes:
                        raise OutputError("output exceeds configured byte limit")
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, destination)
            temporary_path = None
        except OutputError:
            raise
        except OSError:
            raise OutputError("could not write output file") from None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(destination), flags, 0o600)
        with os.fdopen(descriptor, "ab") as handle:
            for chunk in _chunks(payload):
                count += len(chunk)
                if count > max_bytes:
                    raise OutputError("output exceeds configured byte limit")
                handle.write(chunk)
    except OutputError:
        raise
    except DBeeAppError:
        raise
    except OSError:
        raise OutputError("could not write output file") from None


def write_output(step, source_result, context, config, stdout):
    """Format and write one output step within the configured byte limit."""
    payload = None
    try:
        payload = _encode(step["format"], step, source_result, context)
        max_bytes = config["results"]["max_output_bytes"]
        if step["target"]["type"] == "stdout":
            count = 0
            for chunk in _chunks(payload):
                count += len(chunk)
                if count > max_bytes:
                    raise OutputError("output exceeds configured byte limit")
                stdout.buffer.write(chunk) if hasattr(stdout, "buffer") else stdout.write(chunk.decode("utf-8"))
            stdout.flush()
        else:
            _write_file(step["target"]["path"], step.get("mode", "append"), payload, max_bytes)
    except OutputError:
        raise
    except Exception:
        raise OutputError("could not format or write output") from None
    finally:
        close = getattr(payload, "close", None)
        if close:
            close()