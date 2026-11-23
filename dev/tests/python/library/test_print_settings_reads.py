"""Check that Print Sheets reads print settings as their concrete type."""

import ast
from pathlib import Path
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Print Sheets.pushbutton/script.py"
)


def _unwrapped_reads(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    reads = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Attribute)
            and node.attr == "CurrentPrintSetting"
            and isinstance(node.ctx, ast.Load)
        ):
            continue
        parent = parents.get(node)
        wrapped = (
            isinstance(parent, ast.Call)
            and getattr(parent.func, "id", None) == "clr_implementation"
            and node in parent.args
        )
        if not wrapped:
            reads.append(node.lineno)
    return reads


class CurrentPrintSettingTests(unittest.TestCase):
    """pythonnet returns ``CurrentPrintSetting`` as ``IPrintSetting``."""

    def test_every_read_goes_through_clr_implementation(self):
        """Each model's current setting reaches the sheet list as a ``PrintSetting``."""
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))

        self.assertEqual([], _unwrapped_reads(tree))


if __name__ == "__main__":
    unittest.main()
