"""Check how the keynote database passes record values, without Revit."""

import ast
from pathlib import Path
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

MODULE = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Keynotes.pushbutton/keynotesdb.py"
)


def _record_writes(tree):
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("InsertRecord", "UpdateRecord")
    ]


class RecordFieldsTests(unittest.TestCase):
    """pythonnet does not convert a ``dict`` to ``IDictionary<string, object>``."""

    def test_record_values_are_not_python_dicts(self):
        """Adding or editing a keynote must not hand DeffrelDB a Python dict."""
        writes = _record_writes(ast.parse(MODULE.read_text(encoding="utf-8")))

        self.assertEqual(7, len(writes))
        for node in writes:
            with self.subTest(line=node.lineno):
                self.assertNotIsInstance(node.args[3], ast.Dict)


if __name__ == "__main__":
    unittest.main()
