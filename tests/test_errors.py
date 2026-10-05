import unittest

from dbeeapp.errors import (
    ConfigurationError,
    DBeeAppError,
    DatabaseConnectionError,
    InternalError,
    OutputError,
    ProviderError,
    ProviderTimeoutError,
    SQLTimeoutError,
    SQLError,
    TransactionError,
    UsageError,
    ValidationError,
)


class ErrorTaxonomyTests(unittest.TestCase):
    def test_exit_codes_and_categories_are_stable(self):
        cases = (
            (UsageError("usage"), 2, "usage"),
            (ConfigurationError("config"), 3, "configuration"),
            (ValidationError("invalid"), 3, "validation"),
            (ProviderError("provider"), 4, "provider"),
            (ProviderTimeoutError("timeout"), 4, "provider_timeout"),
            (DatabaseConnectionError("connect"), 5, "database_connection"),
            (SQLError("sql"), 6, "sql"),
            (SQLTimeoutError("timeout"), 6, "sql_timeout"),
            (TransactionError("transaction"), 6, "transaction"),
            (OutputError("output"), 7, "output"),
            (DBeeAppError("internal"), 8, "internal"),
            (InternalError("internal"), 8, "internal"),
        )
        for error, exit_code, category in cases:
            with self.subTest(error=type(error).__name__):
                self.assertEqual(error.exit_code, exit_code)
                self.assertEqual(error.category, category)
                self.assertEqual(error.public_message, str(error))


if __name__ == "__main__":
    unittest.main()