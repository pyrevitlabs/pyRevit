"""Check List Elements Of Selected Level never hashes an ElementId."""

import ast
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Analysis.panel/Tools.stack/Inspect.pulldown"
    / "ListElementsOfSelectedLevel.pushbutton/ListElementsOfSelectedLevel_script.py"
)

NEEDED = ("group_elements_by_level", "main")


class _UnhashableId(object):
    """ElementId whose hash code is -1, which CPython rejects."""

    def __init__(self, value):
        self.Value = value
        self.IntegerValue = value

    def __hash__(self):
        raise SystemError("hash code -1")

    def __eq__(self, other):
        return self.Value == other.Value


def _load():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if getattr(node, "name", "") in NEEDED]
    reported = []
    elements = []
    levels = []
    namespace = {
        "defaultdict": defaultdict,
        "DB": SimpleNamespace(
            FilteredElementCollector=lambda doc: SimpleNamespace(
                WhereElementIsNotElementType=lambda: elements
            )
        ),
        "revit": SimpleNamespace(doc=None),
        "forms": SimpleNamespace(select_levels=lambda use_selection: levels),
        "output": SimpleNamespace(print_md=lambda text: None),
        "_t": lambda key: key,
        "get_elementid_value": lambda element_id: element_id.Value,
        "report_level": lambda level, found: reported.append((level, found)),
    }
    exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace, elements, levels, reported


class LevelGroupingTests(unittest.TestCase):
    """Grouping and lookup by level must work when ElementId cannot be hashed."""

    def test_elements_are_reported_under_their_level(self):
        namespace, elements, levels, reported = _load()
        level_a = SimpleNamespace(Id=_UnhashableId(10), Name="A")
        level_b = SimpleNamespace(Id=_UnhashableId(20), Name="B")
        on_a = SimpleNamespace(LevelId=_UnhashableId(10))
        on_b = SimpleNamespace(LevelId=_UnhashableId(20))
        unleveled = SimpleNamespace(LevelId=_UnhashableId(-1))
        elements.extend([on_a, on_b, on_a, unleveled])
        levels.extend([level_a, level_b])

        namespace["main"]()

        self.assertEqual([(level_a, [on_a, on_a]), (level_b, [on_b])], reported)


if __name__ == "__main__":
    unittest.main()
