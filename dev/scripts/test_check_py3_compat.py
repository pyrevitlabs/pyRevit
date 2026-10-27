"""Regression tests for IronPython 3 branch reachability in the static checker."""

import ast
from pathlib import Path
import unittest

try:
    from .check_py3_compat import (
        Finding,
        _is_clr_interface_base,
        _is_engine_guarded,
        _is_generic_list_constructor,
        _is_tracked_extension_finding,
    )
except ImportError:
    from check_py3_compat import (
        Finding,
        _is_clr_interface_base,
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


class NamespaceCompatibilityTests(unittest.TestCase):
    """Revit interface classes keep stable identities across script reloads."""

    def test_revit_interface_classes_have_stable_namespaces(self):
        """Namespaced Python classes can reuse their generated CLR types."""
        root = Path(__file__).resolve().parents[2]
        expected_namespaces = {
            (
                "pyrevitlib/pyrevit/revit/events.py",
                "FuncAsEventHandler",
            ): "pyrevit.revit.events",
            (
                "pyrevitlib/pyrevit/revit/events.py",
                "_GenericExternalEventHandler",
            ): "pyrevit.revit.events",
            (
                "pyrevitlib/pyrevit/revit/selection.py",
                "PickByCategorySelectionFilter",
            ): "pyrevit.revit.selection",
            (
                "pyrevitlib/pyrevit/revit/db/failure.py",
                "FailureSwallower",
            ): "pyrevit.revit.db.failure",
            (
                "pyrevitlib/pyrevit/routes/server/handler.py",
                "RequestHandler",
            ): "pyrevit.routes.server.handler",
            ("pyrevitlib/rpw/ui/selection.py", "SelectionFilter"): "rpw.ui.selection",
            (
                "pyrevitlib/pyrevit/revit/db/create.py",
                "CopyUseDestination",
            ): "pyrevit.revit.db.create",
            (
                "pyrevitlib/pyrevit/revit/dc3dserver.py",
                "Server",
            ): "pyrevit.revit.dc3dserver",
            (
                "pyrevitlib/pyrevit/revit/tmpgfx.py",
                "Handler",
            ): "pyrevit.revit.tmpgfx",
            (
                "pyrevitlib/pyrevit/forms/_ipy.py",
                "_WPFPanelProvider",
            ): "pyrevit.forms._ipy",
            (
                "pyrevitlib/pyrevit/forms/backends/_ipy.py",
                "Reactive",
            ): "pyrevit.forms.backends._ipy",
        }

        for (
            relative_path,
            class_name,
        ), expected_namespace in expected_namespaces.items():
            tree = ast.parse((root / relative_path).read_text(encoding="utf-8"))
            class_node = next(
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name
            )
            namespace_assignment = next(
                node
                for node in class_node.body
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "__namespace__"
                    for target in node.targets
                )
            )
            self.assertEqual(expected_namespace, namespace_assignment.value.value)

    def test_clr_interface_base_is_detected(self):
        """CLR interface implementations require deterministic type identity."""
        interface_base = (
            ast.parse("class Handler(UI.IExternalEventHandler): pass").body[0].bases[0]
        )
        self.assertTrue(_is_clr_interface_base(interface_base))

    def test_non_interface_base_is_not_detected(self):
        """Ordinary Python inheritance does not need a CLR namespace."""
        base = ast.parse("class Handler(BaseHandler): pass").body[0].bases[0]
        self.assertFalse(_is_clr_interface_base(base))


if __name__ == "__main__":
    unittest.main()
