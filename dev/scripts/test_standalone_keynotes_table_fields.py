"""Check how the keynote database defines its table fields, without Revit."""

import ast
from pathlib import Path
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

MODULE = (
    Path(__file__).resolve().parents[2]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Keynotes.pushbutton/keynotesdb.py"
)


def _field_assignments(tree):
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute) and target.attr == "Fields"
            for target in node.targets
        )
    ]


class TableFieldsTests(unittest.TestCase):
    """DeffrelDB hangs Revit on CPython when ``Fields`` is a Python list."""

    def test_fields_are_assigned_as_clr_lists(self):
        """Every ``TableDefinition.Fields`` value is built with ``to_clr_list``."""
        assignments = _field_assignments(ast.parse(MODULE.read_text(encoding="utf-8")))

        self.assertEqual(2, len(assignments))
        for node in assignments:
            with self.subTest(line=node.lineno):
                self.assertIsInstance(node.value, ast.Call)
                self.assertEqual("to_clr_list", getattr(node.value.func, "id", None))


if __name__ == "__main__":
    unittest.main()
