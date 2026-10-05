"""pg8000 DB-API connection construction and safe error translation."""

import ssl
import secrets
from collections import deque

import pg8000.dbapi

from dbeeapp.errors import (
    ConnectionLostError,
    DBeeAppError,
    DatabaseConnectionError,
    SQLError,
    SQLTimeoutError,
)

pg8000.dbapi.paramstyle = "named"


class NoticeBuffer(deque):
    """Bounded pg8000 notice queue that reports how many messages were dropped."""

    def __init__(self, maxlen):
        super().__init__(maxlen=maxlen)
        self.dropped = 0

    def append(self, notice):
        if len(self) == self.maxlen:
            self.dropped += 1
        super().append(notice)

    def take_dropped(self):
        dropped, self.dropped = self.dropped, 0
        return dropped


def connect(database, password, config):
    """Open a PostgreSQL connection with explicit TLS and finite connect timeout."""
    ssl_settings = database.get("ssl", {})
    ssl_mode = ssl_settings.get("mode", config["postgresql"]["ssl_mode"])
    ca_file = ssl_settings.get("ca_file", config["postgresql"].get("ca_file"))
    if ssl_mode == "disable":
        ssl_context = False
    else:
        ssl_context = ssl.create_default_context(cafile=ca_file)
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
    try:
        connection = pg8000.dbapi.connect(
            user=database["user"],
            password=password,
            host=database["host"],
            port=database.get("port", 5432),
            database=database["database"],
            ssl_context=ssl_context,
            timeout=float(database.get("connect_timeout", config["timeouts"]["connect"])),
            application_name="DBeeApp",
        )
        connection.notices = NoticeBuffer(config.get("server_output", {}).get("max_messages", 1000))
        return connection
    except Exception:
        raise DatabaseConnectionError("could not establish PostgreSQL connection") from None


def execute(cursor, sql, params, timeout):
    """Execute SQL with bound named values, normalize driver errors safely."""
    try:
        if timeout:
            cursor.execute(
                "SELECT set_config('statement_timeout', :timeout_ms, true)",
                {"timeout_ms": str(max(1, int(timeout * 1000)))},
            )
        _execute_bound(cursor, sql, params)
    except pg8000.dbapi.InterfaceError:
        raise ConnectionLostError("PostgreSQL connection was lost during SQL execution") from None
    except pg8000.dbapi.Error as error:
        raise_database_error(error)
    except DBeeAppError:
        raise
    except Exception:
        raise SQLError("SQL execution failed") from None

def _execute_bound(cursor, sql, params=None):
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)


def execute_stream(cursor, sql, params, timeout, batch_size, notice_callback=None):
    """Declare an internal server-side cursor and prefetch one bounded batch."""
    try:
        if timeout:
            _execute_bound(
                cursor,
                "SELECT set_config('statement_timeout', :timeout_ms, true)",
                {"timeout_ms": str(max(1, int(timeout * 1000)))},
            )
        name = "dbeeapp_stream_" + secrets.token_hex(8)
        _execute_bound(cursor, "DECLARE {} NO SCROLL CURSOR FOR {}".format(name, sql), params)
        _execute_bound(cursor, "FETCH FORWARD {} FROM {}".format(batch_size, name))
        first_batch = cursor.fetchmany(batch_size)
        return StreamingCursor(cursor, name, batch_size, first_batch, notice_callback=notice_callback)
    except pg8000.dbapi.InterfaceError:
        raise ConnectionLostError("PostgreSQL connection was lost while starting result stream") from None
    except pg8000.dbapi.Error as error:
        raise_database_error(error)
    except DBeeAppError:
        raise
    except Exception:
        raise SQLError("could not start PostgreSQL result stream") from None

class StreamingCursor:
    """DB-API cursor facade backed by a PostgreSQL server-side cursor."""

    def __init__(self, cursor, name, batch_size, first_batch, notice_callback=None):
        self.cursor = cursor
        self.name = name
        self.batch_size = batch_size
        self.first_batch = list(first_batch)
        self.first_pending = True
        self.description = cursor.description
        self.closed = False
        self.notice_callback = notice_callback

    def fetchmany(self, size=None):
        size = size or self.batch_size
        if self.first_pending:
            self.first_pending = False
            if len(self.first_batch) <= size:
                return self.first_batch
            rows, self.first_batch = self.first_batch[:size], self.first_batch[size:]
            self.first_pending = True
            return rows
        try:
            _execute_bound(self.cursor, "FETCH FORWARD {} FROM {}".format(size, self.name))
            rows = self.cursor.fetchmany(size)
            if self.notice_callback:
                self.notice_callback()
            return rows
        except pg8000.dbapi.Error as error:
            raise_database_error(error)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            _execute_bound(self.cursor, "CLOSE {}".format(self.name))
        except pg8000.dbapi.Error as error:
            raise_database_error(error)
        finally:
            self.cursor.close()


def raise_database_error(error):
    """Raise a safe categorized error from a pg8000 DB-API exception."""
    if isinstance(error, pg8000.dbapi.InterfaceError):
        raise ConnectionLostError("PostgreSQL connection was lost during database operation") from None
    details = error.args[0] if error.args and isinstance(error.args[0], dict) else {}
    sqlstate = getattr(error, "sqlstate", None) or details.get("C")
    if sqlstate == "57014":
        raise SQLTimeoutError("PostgreSQL statement timed out") from None
    raise SQLError("PostgreSQL rejected the database operation") from None


def commit(connection):
    """Commit a statement boundary without hiding connection loss ambiguity."""
    try:
        connection.commit()
    except pg8000.dbapi.InterfaceError:
        raise ConnectionLostError("PostgreSQL connection was lost while committing") from None
    except pg8000.dbapi.Error:
        raise SQLError("PostgreSQL transaction could not be committed") from None


def rollback(connection):
    """Rollback a statement boundary, normalizing driver errors safely."""
    try:
        connection.rollback()
    except pg8000.dbapi.InterfaceError:
        raise ConnectionLostError("PostgreSQL connection was lost while rolling back") from None
    except pg8000.dbapi.Error:
        raise SQLError("PostgreSQL transaction could not be rolled back") from None