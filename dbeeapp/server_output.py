"""Bounded routing for PostgreSQL server NOTICE/INFO/LOG messages."""

from pathlib import Path


def drain_notices(connection):
    """Remove and return queued notices plus the number dropped by the buffer."""
    queue = getattr(connection, "notices", None)
    if queue is None:
        return [], 0
    messages = list(queue)
    queue.clear()
    take_dropped = getattr(queue, "take_dropped", None)
    dropped = take_dropped() if take_dropped else 0
    return messages, dropped


def _message_text(notice, max_bytes):
    if not isinstance(notice, dict):
        return None
    message = notice.get("M", notice.get(b"M"))
    if isinstance(message, bytes):
        message = message.decode("utf-8", errors="replace")
    if not isinstance(message, str):
        return None
    severity = notice.get("V", notice.get(b"V")) or notice.get("S", notice.get(b"S")) or "NOTICE"
    if isinstance(severity, bytes):
        severity = severity.decode("ascii", errors="replace")
    if not isinstance(severity, str):
        severity = "NOTICE"
    severity = severity.replace("\r", "\\r").replace("\n", "\\n")
    message = message.replace("\r", "\\r").replace("\n", "\\n")
    encoded = message.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        suffix = b"... [message truncated]"
        encoded = encoded[:max(0, max_bytes - len(suffix))] + suffix[:max_bytes]
        message = encoded.decode("utf-8", errors="ignore")
    return severity, message


def route_notices(notices, dropped, config, stdout, logger, job_id, step_id, database_id):
    """Emit only the notice severity/message to explicitly enabled destinations."""
    settings = config.get("server_output", {})
    stdout_enabled = settings.get("stdout", False)
    file_path = settings.get("file")
    if not stdout_enabled and not file_path:
        return

    lines = []
    max_bytes = settings.get("max_message_bytes", 8192)
    for notice in notices:
        parsed = _message_text(notice, max_bytes)
        if parsed is None:
            continue
        severity, message = parsed
        lines.append("[PostgreSQL {}] job={} step={} db={}: {}".format(severity, job_id, step_id, database_id, message))
    if dropped:
        lines.append("[PostgreSQL NOTICE] job={} step={} db={}: {} server messages omitted by the configured buffer limit".format(job_id, step_id, database_id, dropped))
    if not lines:
        return

    for line in lines:
        if stdout_enabled:
            try:
                stdout.write(line + "\n")
                stdout.flush()
            except Exception:
                logger.warning("PostgreSQL server output could not be written to stdout")
    if file_path:
        try:
            path = Path(file_path)
            with path.open("a", encoding="utf-8") as handle:
                for line in lines:
                    handle.write(line + "\n")
        except OSError:
            logger.warning("PostgreSQL server output file could not be written")