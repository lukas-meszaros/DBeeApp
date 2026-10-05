import unittest

from dbeeapp.errors import SQLError
from dbeeapp.results import collect_result

_DEFAULT_DESCRIPTION = object()


class FakeCursor:
    def __init__(self, rows, description=_DEFAULT_DESCRIPTION):
        self.rows = list(rows)
        self.description = [("value",), ("label",)] if description is _DEFAULT_DESCRIPTION else description
        self.rowcount = len(self.rows)

    def fetchmany(self, size):
        result, self.rows = self.rows[:size], self.rows[size:]
        return result


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.config = {"results": {"fetch_batch_size": 2, "max_rows": 3, "max_bytes": 1000}}

    def test_first_and_rows_modes(self):
        first = collect_result(FakeCursor([(1, "a"), (2, "b")]), "first", self.config)
        self.assertEqual(first["first"], {"value": 1, "label": "a"})
        rows = collect_result(FakeCursor([(1, "a"), (2, "b")]), "rows", self.config)
        self.assertEqual(rows["row_count"], 2)
        self.assertEqual(len(rows["rows"]), 2)

    def test_scalar_shape_is_enforced(self):
        with self.assertRaises(SQLError):
            collect_result(FakeCursor([(1, "a")]), "scalar", self.config)

    def test_rows_fail_instead_of_truncating(self):
        with self.assertRaisesRegex(SQLError, "safety limit"):
            collect_result(FakeCursor([(1, "a"), (2, "b"), (3, "c"), (4, "d")]), "rows", self.config)

    def test_stream_yields_bounded_batches(self):
        result = collect_result(FakeCursor([(1, "a"), (2, "b"), (3, "c")]), "stream", self.config)
        self.assertEqual([row["value"] for row in result["stream"]], [1, 2, 3])

    def test_non_row_statement_uses_affected_count_without_fetching(self):
        cursor = FakeCursor([], description=None)
        cursor.rowcount = 3
        result = collect_result(cursor, "none", self.config)
        self.assertEqual(result["row_count"], 3)


if __name__ == "__main__":
    unittest.main()