"""Application errors safe to display to users."""


class DBeeAppError(Exception):
    """A categorized error with a deliberately safe public message."""

    exit_code = 8
    category = "internal"

    def __init__(self, message):
        super().__init__(message)
        self.public_message = message


class InternalError(DBeeAppError):
    exit_code = 8
    category = "internal"


class UsageError(DBeeAppError):
    exit_code = 2
    category = "usage"


class ConfigurationError(DBeeAppError):
    exit_code = 3
    category = "configuration"


class ValidationError(DBeeAppError):
    exit_code = 3
    category = "validation"


class ProviderError(DBeeAppError):
    exit_code = 4
    category = "provider"


class ProviderTimeoutError(ProviderError):
    category = "provider_timeout"


class DatabaseConnectionError(DBeeAppError):
    exit_code = 5
    category = "database_connection"


class ConnectionLostError(DBeeAppError):
    exit_code = 5
    category = "connection_lost"


class SQLError(DBeeAppError):
    exit_code = 6
    category = "sql"


class SQLTimeoutError(SQLError):
    category = "sql_timeout"


class TransactionError(DBeeAppError):
    exit_code = 6
    category = "transaction"


class OutputError(DBeeAppError):
    exit_code = 7
    category = "output"