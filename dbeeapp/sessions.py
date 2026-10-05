"""Small per-job registry for reusable and temporary PostgreSQL sessions."""

from contextlib import contextmanager

from dbeeapp.credentials import invoke_provider
from dbeeapp.database import connect
from dbeeapp.errors import ConnectionLostError, DatabaseConnectionError, ProviderError


class SessionManager:
    """Own lazy reusable connections and temporary per-step connections."""

    def __init__(self, databases, config, connector=None, provider=None):
        self.databases = databases
        self.config = config
        self.connector = connector or connect
        self.provider = provider or invoke_provider
        self.reusable = {}
        self.invalid = set()

    def _open(self, database_id):
        database = self.databases[database_id]
        credential = database["credential"]
        try:
            password = self.provider(
                self.config["provider_dir"],
                credential["provider"],
                database["user"],
                credential.get("options", {}),
                self.config["timeouts"]["provider"],
            )
            connection = self.connector(database, password, self.config)
        except (ProviderError, DatabaseConnectionError):
            raise
        except Exception:
            raise DatabaseConnectionError("could not open PostgreSQL session") from None
        finally:
            if "password" in locals():
                del password
        return connection

    @contextmanager
    def session(self, database_id, mode="reuse"):
        if database_id in self.invalid:
            raise ConnectionLostError("reusable PostgreSQL session is invalid")
        temporary = mode == "new"
        connection = None
        try:
            if temporary:
                connection = self._open(database_id)
            else:
                connection = self.reusable.get(database_id)
                if connection is None:
                    connection = self._open(database_id)
                    self.reusable[database_id] = connection
            yield connection
        except ConnectionLostError:
            if not temporary:
                self.invalidate(database_id)
            raise
        finally:
            if temporary and connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def invalidate(self, database_id):
        """Mark a reusable connection unusable and close it best-effort."""
        self.invalid.add(database_id)
        connection = self.reusable.pop(database_id, None)
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def close_all(self):
        """Attempt all close operations even if one connection close fails."""
        connections = list(self.reusable.values())
        self.reusable.clear()
        for connection in connections:
            try:
                connection.close()
            except Exception:
                pass