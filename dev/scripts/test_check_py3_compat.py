"""Regression tests for IronPython 3 branch reachability in the static checker."""

import ast
from pathlib import Path
import tempfile
import textwrap
import unittest
from pathlib import Path

try:
    from .check_py3_compat import (
        Finding,
        check_file,
        _is_engine_guarded,
        _is_generic_list_constructor,
        _is_tracked_extension_finding,
    )
except ImportError:
    from check_py3_compat import (
        Finding,
        check_file,
        _is_engine_guarded,
        _is_generic_list_constructor,
        _is_tracked_extension_finding,
    )


def _unicode_reachability(source):
    tree = ast.parse(source)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return [
        _is_engine_guarded(node, parents)
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id == "unicode"
    ]


class EngineGuardTests(unittest.TestCase):
    """Engine guards only suppress code that cannot run on IronPython 3."""

    def test_ironpython_branch_remains_reachable(self):
        """IRONPY includes IronPython 3 and must not hide Python 2 names."""
        self.assertEqual([False], _unicode_reachability("if IRONPY:\n    unicode(1)"))

    def test_python_two_branch_is_unreachable(self):
        """Python 2 branches are safe to exclude from the IPY3 scan."""
        self.assertEqual([True], _unicode_reachability("if PY2:\n    unicode(1)"))

    def test_python_two_else_branch_is_reachable(self):
        """The opposite side of a false condition still needs checking."""
        self.assertEqual(
            [False], _unicode_reachability("if PY2:\n    pass\nelse:\n    unicode(1)")
        )

    def test_composite_branch_uses_known_flag_values(self):
        """An unknown condition cannot hide a definitely false IPY3 branch."""
        self.assertEqual(
            [True],
            _unicode_reachability("if IRONPY and PY2 and custom:\n    unicode(1)"),
        )

    def test_skip_unless_ironpython_does_not_hide_body(self):
        """A test enabled on IPY3 still needs its body checked."""
        self.assertEqual(
            [False],
            _unicode_reachability(
                "@unittest.skipUnless(IRONPY, 'reason')\ndef test():\n    unicode(1)"
            ),
        )

    def test_skip_unless_python_two_hides_body(self):
        """A test disabled on IPY3 does not execute its body there."""
        self.assertEqual(
            [True],
            _unicode_reachability(
                "@unittest.skipUnless(PY2, 'reason')\ndef test():\n    unicode(1)"
            ),
        )


class GenericCollectionTests(unittest.TestCase):
    """Generic CLR construction must not depend on IronPython coercion."""

    def test_list_constructor_with_values_is_detected(self):
        """A generic List receiving Python values needs Add-based construction."""
        call = ast.parse("List[DB.ElementId](element_ids)").body[0].value
        self.assertTrue(_is_generic_list_constructor(call))

    def test_empty_list_constructor_is_not_detected(self):
        """The parameterless generic List constructor is portable."""
        call = ast.parse("List[DB.ElementId]()").body[0].value
        self.assertFalse(_is_generic_list_constructor(call))

    def test_python_iterable_arguments_are_detected(self):
        """Literal containers, comprehensions and iterable builtins need Add."""
        for source in (
            "List[int]([1, 2])",
            "List[int]((1, 2))",
            "List[int]({1, 2})",
            "List[int]([x for x in xs])",
            "List[int](x for x in xs)",
            "List[int](list(xs))",
            "List[int](sorted(xs))",
            "framework.List[DB.ElementId](element_ids)",
            "Generic.List[DB.Curve]([curve])",
            "System.Collections.Generic.List[str](names)",
        ):
            with self.subTest(source=source):
                call = ast.parse(source).body[0].value
                self.assertTrue(_is_generic_list_constructor(call))

    def test_clr_and_capacity_arguments_are_not_detected(self):
        """Capacities and CLR collections from API calls are portable."""
        for source in (
            "List[DB.ElementId](10)",
            "List[DB.ElementId](uidoc.Selection.GetElementIds())",
            "List[DB.ElementId](el.GetTaggedLocalElementIds())",
            "framework.List[DB.ElementId](self.element_ids)",
            "Dictionary[str, int](names)",
        ):
            with self.subTest(source=source):
                call = ast.parse(source).body[0].value
                self.assertFalse(_is_generic_list_constructor(call))

    def test_bundled_extension_list_finding_is_tracked(self):
        """Known extension migrations stay visible without blocking the library gate."""
        path = Path(__file__).resolve().parents[2] / "extensions" / "Tool.py"
        self.assertTrue(_is_tracked_extension_finding(Finding(path, 1, "CLR-LIST", "")))

    def test_external_extension_list_finding_blocks(self):
        """Third-party extension checks still report CLR collection incompatibility."""
        self.assertFalse(
            _is_tracked_extension_finding(
                Finding(Path("C:/extension/Tool.py"), 1, "CLR-LIST", "")
            )
        )


class ClrRuleScopeTests(unittest.TestCase):
    """CLR collection rules respect engine guards and CLR values."""

    def _codes(self, source):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.py"
            path.write_text(textwrap.dedent(source), encoding="utf-8")
            return [finding.code for finding in check_file(path)]

    def test_ironpython_only_branches_are_not_flagged(self):
        """Code under ``if PY2:`` or ``if IRONPY:`` never runs on CPython."""
        self.assertEqual(
            [],
            self._codes(
                """
                if PY2:
                    ids = List[DB.ElementId](element_ids)
                    class Handler(UI.IExternalEventHandler):
                        pass
                if IRONPY:
                    ids = List[DB.ElementId](element_ids)
                    class Provider(UI.IDockablePaneProvider):
                        pass
                """
            ),
        )

    def test_names_bound_to_clr_values_or_capacities_are_not_flagged(self):
        """CLR results and counts passed by name are not Python iterables."""
        self.assertEqual(
            [],
            self._codes(
                """
                def build(uidoc, items):
                    current = uidoc.Selection.GetElementIds()
                    count = len(items)
                    capacity = 10
                    return (
                        List[DB.ElementId](current),
                        List[DB.ElementId](count),
                        List[DB.ElementId](capacity),
                    )
                """
            ),
        )

    def test_names_bound_to_python_values_are_flagged(self):
        """A name assigned a Python list, or by a Python helper, is reported."""
        self.assertEqual(
            ["CLR-LIST", "CLR-LIST", "CLR-LIST"],
            self._codes(
                """
                def build(curves, element_ids):
                    ids = []
                    ordered = sort_curves(curves)
                    return (
                        List[DB.ElementId](ids),
                        List[DB.Curve](ordered),
                        List[DB.ElementId](element_ids),
                    )
                """
            ),
        )

    def test_assignments_in_other_functions_and_shadowing_parameters_are_ignored(self):
        """Only lexically applicable assignments mark a name as a CLR value."""
        self.assertEqual(
            ["CLR-LIST", "CLR-LIST"],
            self._codes(
                """
                count = 10

                def unrelated():
                    values = 10

                def convert(values, count):
                    return List[int](values), List[int](count)
                """
            ),
        )


class NamedIndexerTests(unittest.TestCase):
    """CLR named indexers must use the accessor that pythonnet exposes."""

    def _codes(self, source):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.py"
            path.write_text(source, encoding="utf-8")
            return [finding.code for finding in check_file(path)]

    def test_parameter_indexer_is_flagged(self):
        """The IronPython-only subscript form is reported."""
        self.assertEqual(
            ["CLR-NAMED-INDEXER"],
            self._codes("el.Parameter[DB.BuiltInParameter.ALL_MODEL_MARK]"),
        )

    def test_get_parameter_accessor_is_clean(self):
        """The engine-portable accessor is not reported."""
        self.assertEqual(
            [], self._codes("el.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)")
        )

    def test_parameters_collection_index_is_clean(self):
        """Indexing an unrelated attribute is not a named indexer."""
        self.assertEqual([], self._codes("first = el.Parameters[0]"))

    def test_ironpython_only_branch_is_clean(self):
        """An indexer behind an IronPython guard never runs on CPython."""
        for guard in ("IRONPY", "compat.IRONPY", "IRONPY2 or IRONPY3"):
            with self.subTest(guard=guard):
                self.assertEqual(
                    [],
                    self._codes(
                        "if {}:\n"
                        "    value = el.Parameter[bip]\n"
                        "else:\n"
                        "    value = el.get_Parameter(bip)\n".format(guard)
                    ),
                )

    def test_else_of_cpython_branch_is_clean(self):
        """The else side of a CPython-true guard never runs on CPython."""
        for guard in ("PY3", "not IRONPY", "not compat.IRONPY"):
            with self.subTest(guard=guard):
                self.assertEqual(
                    [],
                    self._codes(
                        "if {}:\n"
                        "    value = el.get_Parameter(bip)\n"
                        "else:\n"
                        "    value = el.Parameter[bip]\n".format(guard)
                    ),
                )

    def test_cpython_reachable_branches_are_flagged(self):
        """Guards that leave the indexer reachable on CPython still report it."""
        for source in (
            "if PY3:\n    value = el.Parameter[bip]\n",
            "if not IRONPY:\n    value = el.Parameter[bip]\n",
            "if IRONPY:\n    pass\nelse:\n    value = el.Parameter[bip]\n",
            "if custom:\n    value = el.Parameter[bip]\n",
            "value = PY3 and el.Parameter[bip]\n",
            "value = IRONPY or el.Parameter[bip]\n",
            "value = el.Parameter[bip] if PY3 else None\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(["CLR-NAMED-INDEXER"], self._codes(source))

    def test_short_circuit_and_conditional_guards_are_clean(self):
        """Operands and branches CPython never evaluates are not reported."""
        for source in (
            "value = IRONPY and el.Parameter[bip]\n",
            "value = compat.IRONPY and el.Parameter[bip]\n",
            "value = PY3 or el.Parameter[bip]\n",
            "value = el.Parameter[bip] if IRONPY else el.get_Parameter(bip)\n",
            "value = el.get_Parameter(bip) if PY3 else el.Parameter[bip]\n",
        ):
            with self.subTest(source=source):
                self.assertEqual([], self._codes(source))

    def test_flags_on_other_objects_do_not_guard(self):
        """Only pyRevit's compat flags are engine guards."""
        for guard in ("options.IRONPY", "self.IRONPY"):
            with self.subTest(guard=guard):
                self.assertEqual(
                    ["CLR-NAMED-INDEXER"],
                    self._codes(
                        "if {}:\n    value = el.Parameter[bip]\n".format(guard)
                    ),
                )
        self.assertEqual(
            [],
            self._codes("if pyrevit.compat.IRONPY:\n    value = el.Parameter[bip]\n"),
        )


if __name__ == "__main__":
    unittest.main()
