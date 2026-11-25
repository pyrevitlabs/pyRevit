"""Regression for #4178: List Elements Of Selected Level never hashes an ElementId."""

import ast
import functools
from collections import defaultdict
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

import pytest


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

    def __init__(self, attribute, value):
        self._attribute = attribute
        setattr(self, attribute, value)

    def __hash__(self):
        raise SystemError("hash code -1")

    def __eq__(self, other):
        return getattr(self, self._attribute) == getattr(other, self._attribute)


def _is_needed(node):
    if getattr(node, "name", "") in NEEDED:
        return True
    if isinstance(node, ast.ImportFrom) and node.module == "pyrevit":
        node.names = [alias for alias in node.names if alias.name == "compat"]
        return bool(node.names)
    return (
        isinstance(node, ast.Assign)
        and getattr(node.targets[0], "id", "") == "get_elementid_value"
    )


def _load(attribute):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if _is_needed(node)]
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
        "report_level": lambda level, found: reported.append((level, found)),
    }
    pyrevit_stub = SimpleNamespace(
        compat=SimpleNamespace(
            get_elementid_value_func=lambda: (
                lambda element_id: getattr(element_id, attribute)
            )
        )
    )
    with mock.patch.dict(sys.modules, {"pyrevit": pyrevit_stub}):
        exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace, elements, levels, reported


@pytest.mark.regression
class LevelGroupingTests(unittest.TestCase):
    """Grouping and lookup by level must work when ElementId cannot be hashed."""

    def test_elements_are_reported_under_their_level(self):
        """Each level reports only its own elements, on old and new id APIs."""
        for attribute in ("IntegerValue", "Value"):
            with self.subTest(attribute=attribute):
                self._assert_grouping(attribute)

    def _assert_grouping(self, attribute):
        namespace, elements, levels, reported = _load(attribute)
        make_id = functools.partial(_UnhashableId, attribute)
        level_a = SimpleNamespace(Id=make_id(10), Name="A")
        level_b = SimpleNamespace(Id=make_id(20), Name="B")
        on_a = SimpleNamespace(LevelId=make_id(10))
        on_b = SimpleNamespace(LevelId=make_id(20))
        unleveled = SimpleNamespace(LevelId=make_id(-1))
        elements.extend([on_a, on_b, on_a, unleveled])
        levels.extend([level_a, level_b])

        namespace["main"]()

        self.assertEqual([(level_a, [on_a, on_a]), (level_b, [on_b])], reported)


if __name__ == "__main__":
    unittest.main()
