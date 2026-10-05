import unittest

from dbeeapp.conditions import evaluate_condition
from dbeeapp.errors import ValidationError
from dbeeapp.resolver import render_text, resolve_value


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "vars": {"count": 4, "name": "alpha"},
            "steps": {"lookup": {"first": {"id": 8}, "row_count": 1, "status": "success"}},
        }

    def test_full_placeholder_preserves_value_type(self):
        self.assertEqual(resolve_value("{{ vars.count }}", self.context), 4)
        self.assertEqual(resolve_value("{{ steps.lookup.first.id }}", self.context), 8)

    def test_unknown_namespace_and_value_fail(self):
        for value in ("{{ password }}", "{{ vars.missing }}", "{{ vars.name.upper() }}"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                resolve_value(value, self.context)

    def test_output_text_interpolates_scalars_only(self):
        self.assertEqual(render_text("{{ vars.name }}={{ result }}", self.context, 7), "alpha=7")
        self.assertEqual(render_text("{{ result }}", self.context, {"id": 4}), '{"id":4}')


class ConditionTests(unittest.TestCase):
    def test_comparisons_and_empty_conditions(self):
        context = {"vars": {"n": 3, "items": []}, "steps": {"read": {"row_count": 3, "status": "success"}}}
        self.assertTrue(evaluate_condition({"greater_than": {"left": "{{ vars.n }}", "right": 2}}, context))
        self.assertTrue(evaluate_condition({"empty": "{{ vars.items }}"}, context))
        self.assertTrue(evaluate_condition({"row_count": {"step": "read", "operator": "gte", "value": 2}}, context))
        self.assertTrue(evaluate_condition({"success": "{{ steps.read.status }}"}, context))

    def test_incompatible_comparison_fails(self):
        with self.assertRaises(ValidationError):
            evaluate_condition({"greater_than": {"left": "x", "right": 4}}, {"vars": {}, "steps": {}})


if __name__ == "__main__":
    unittest.main()