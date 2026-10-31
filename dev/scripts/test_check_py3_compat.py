"""Regression tests for IronPython 3 branch reachability in the static checker."""

import ast
from pathlib import Path
import tempfile
import textwrap
import unittest

try:
    from .check_py3_compat import (
        FORM_BASES,
        Finding,
        _bundle_engine_type,
        check_file,
        _is_clr_interface_base,
        _is_engine_guarded,
        _is_generic_list_constructor,
        _has_stable_clr_namespace,
        _is_tracked_extension_finding,
        _bundle_engine_type_from_regex,
        _may_run_under_cpython,
        _native_form_uses,
    )
except ImportError:
    from check_py3_compat import (
        FORM_BASES,
        Finding,
        _bundle_engine_type,
        check_file,
        _is_clr_interface_base,
        _is_engine_guarded,
        _is_generic_list_constructor,
        _has_stable_clr_namespace,
        _is_tracked_extension_finding,
        _bundle_engine_type_from_regex,
        _may_run_under_cpython,
        _native_form_uses,
    )


def _form_usages(source):
    return [
        usage
        for node in ast.walk(ast.parse(textwrap.dedent(source)))
        if isinstance(node, ast.ClassDef)
        for _, usage in _native_form_uses(node)
    ]


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

    def test_non_callback_clr_interface_is_not_detected(self):
        """Unsupported CLR interface implementations retain pythonnet defaults."""
        interface_base = (
            ast.parse("class Server(dc3d.IDirectContext3DServer): pass")
            .body[0]
            .bases[0]
        )
        self.assertFalse(_is_clr_interface_base(interface_base))

    def test_literal_namespace_is_stable(self):
        """A fixed string keeps a generated CLR name reusable on reload."""
        class_node = ast.parse(
            'class Handler(UI.IExternalEventHandler):\n    __namespace__ = "test"'
        ).body[0]
        self.assertTrue(_has_stable_clr_namespace(class_node))

    def test_runtime_namespace_is_not_stable(self):
        """Execution-specific names recreate the type on every reload."""
        class_node = ast.parse(
            "class Handler(UI.IExternalEventHandler):\n    __namespace__ = exec_id"
        ).body[0]
        self.assertFalse(_has_stable_clr_namespace(class_node))


class NativeFormUseTests(unittest.TestCase):
    """Forms handing themselves to WPF break when the form wraps a native root."""

    def test_owner_assignment_from_a_form_is_detected(self):
        """WPF requires a native Window as an owner, not the Python controller."""
        usages = _form_usages(
            """
            class Tool(forms.WPFWindow):
                def open(self, child):
                    child.Owner = self
            """
        )
        self.assertEqual(["`.Owner = self`"], usages)

    def test_interop_and_type_checks_on_a_form_are_detected(self):
        """Interop handles and type checks need the native root."""
        usages = _form_usages(
            """
            class Pane(WPFPanel):
                def handle(self):
                    isinstance(self, Page)
                    return WindowInteropHelper(self).Handle
            """
        )
        self.assertEqual(
            ["`isinstance(self, Page)`", "`WindowInteropHelper(self)`"], usages
        )

    def test_unwrapped_root_and_plain_classes_are_not_detected(self):
        """Unwrapped roots and classes that are not forms stay clean."""
        usages = _form_usages(
            """
            class Tool(forms.WPFWindow):
                def open(self, child):
                    child.Owner = _backend.unwrap(self)

            class Helper(object):
                def bind(self, child):
                    child.Owner = self
            """
        )
        self.assertEqual([], usages)

    def test_nested_classes_are_checked_only_on_their_own(self):
        """A nested helper's self is not the form, and nested forms report once."""
        usages = _form_usages(
            """
            class Tool(forms.WPFWindow):
                class Helper(object):
                    def bind(self, child):
                        child.Owner = self

                class Inner(forms.WPFWindow):
                    def open(self, child):
                        child.Owner = self
            """
        )
        self.assertEqual(["`.Owner = self`"], usages)

    def test_only_code_that_can_run_under_cpython_is_checked(self):
        """IronPython scripts may hand their CLR-derived form to WPF directly."""
        root = Path(__file__).resolve().parents[2]
        script = root / "extensions" / "Tool.pushbutton" / "script.py"
        self.assertTrue(
            _may_run_under_cpython(root / "pyrevitlib" / "pyrevit" / "x.py", "")
        )
        self.assertFalse(_may_run_under_cpython(script, "import clr"))
        self.assertTrue(_may_run_under_cpython(script, "#! python3"))
        self.assertTrue(_may_run_under_cpython(script, "#! cpython"))

    def test_first_line_rule_matches_the_runtime(self):
        """Like ScriptRuntime, any first line containing the marker counts, case-sensitively."""
        root = Path(__file__).resolve().parents[2]
        script = root / "extensions" / "Tool.pushbutton" / "script.py"
        self.assertTrue(_may_run_under_cpython(script, "# requires python3\nx = 1"))
        self.assertTrue(_may_run_under_cpython(script, "# cpython engine"))
        self.assertFalse(_may_run_under_cpython(script, "#! Python3"))
        self.assertFalse(_may_run_under_cpython(script, "#! CPython"))
        self.assertFalse(_may_run_under_cpython(script, "import clr\n#! python3"))

    def test_extension_and_bundle_engine_declarations_enable_the_check(self):
        """Scripts made CPython by their extension or bundle are checked too."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            declared = root / "Declared.extension"
            bundle = declared / "Tab.tab" / "Panel.panel" / "Tool.pushbutton"
            bundle.mkdir(parents=True)
            script = bundle / "script.py"
            (declared / "extension.json").write_text('{"engine": {"type": "CPython"}}')
            self.assertTrue(_may_run_under_cpython(script, "import clr"))

            plain = root / "Plain.extension" / "Tool.pushbutton"
            plain.mkdir(parents=True)
            plain_script = plain / "script.py"
            self.assertFalse(_may_run_under_cpython(plain_script, "import clr"))
            (plain / "bundle.yaml").write_text(
                "title: Tool\nengine:\n  type: cpython\n"
            )
            self.assertTrue(_may_run_under_cpython(plain_script, "import clr"))

    def _bundle_script(self, root, bundle_yaml, extension_json=None):
        extension = root / "Ext.extension"
        bundle = extension / "Tool.pushbutton"
        bundle.mkdir(parents=True)
        if extension_json is not None:
            (extension / "extension.json").write_text(extension_json)
        (bundle / "bundle.yaml").write_text(bundle_yaml)
        return bundle / "script.py"

    def test_flow_style_bundle_engine_is_read(self):
        """``engine: {type: cpython}`` declares CPython like the block form."""
        with tempfile.TemporaryDirectory() as directory:
            script = self._bundle_script(
                Path(directory), "title: Tool\nengine: {type: CPython, clean: true}\n"
            )
            self.assertTrue(_may_run_under_cpython(script, "import clr"))

    def test_bundle_engine_type_wins_over_extension(self):
        """A bundle's own ironpython type overrides a cpython extension."""
        with tempfile.TemporaryDirectory() as directory:
            script = self._bundle_script(
                Path(directory),
                "engine:\n  type: IronPython\n",
                '{"engine": "cpython"}',
            )
            self.assertFalse(_may_run_under_cpython(script, "#! python3"))

    def test_bundle_engine_regex_fallback_reads_both_styles(self):
        """Without PyYAML the regex fallback still reads block and flow styles."""
        for text, expected in (
            ("engine:\n  clean: true\n  type: cpython\n", "cpython"),
            ("engine: {clean: true, type: 'CPython'}\n", "CPython"),
            ("title: x\nengine:\n  clean: true\nother:\n  type: cpython\n", None),
            ("title: x\n", None),
        ):
            with self.subTest(text=text):
                self.assertEqual(expected, _bundle_engine_type_from_regex(text))

    def test_unknown_bundle_engine_type_replaces_the_extension_default(self):
        """Like the runtime, any non-blank bundle type drops the extension default."""
        with tempfile.TemporaryDirectory() as directory:
            script = self._bundle_script(
                Path(directory), "engine:\n  type: python3\n", '{"engine": "cpython"}'
            )
            self.assertFalse(_may_run_under_cpython(script, "import clr"))
            self.assertTrue(_may_run_under_cpython(script, "#! python3"))

    def test_bundle_yaml_parse_error_falls_back_to_the_regex(self):
        """Text PyYAML rejects still yields the engine type without PyYAML's help."""
        with tempfile.TemporaryDirectory() as directory:
            script = self._bundle_script(
                Path(directory), "engine:\n  type: cpython\ntitle: [unclosed\n"
            )
            self.assertEqual("cpython", _bundle_engine_type(script))

    def test_custom_yaml_tags_do_not_hide_the_engine_type(self):
        """Tags YamlDotNet accepts but safe_load rejects keep the declared type."""
        with tempfile.TemporaryDirectory() as directory:
            script = self._bundle_script(
                Path(directory),
                "title: !custom Tool\nengine:\n  type: cpython\n",
                '{"engine": "ironpython"}',
            )
            self.assertEqual("cpython", _bundle_engine_type(script))
            self.assertTrue(_may_run_under_cpython(script, "import clr"))

    def test_form_bases_are_the_exported_form_classes(self):
        """FORM_BASES follows forms/_common.py exports, filtered to form classes."""
        self.assertLessEqual(
            {"WPFWindow", "WPFPanel", "SelectFromList", "ProgressBar"}, FORM_BASES
        )
        self.assertFalse({"Reactive", "TemplateListItem", "alert"} & FORM_BASES)

    def test_rules_report_in_registry_order(self):
        """Each node reports its rules in order, after file-level rules."""
        source = textwrap.dedent(
            """
            import StringIO
            class It(object):
                def __iter__(self):
                    return self
                def next(self):
                    return d.iteritems()
                def __nonzero__(self):
                    return xrange(1)
            """
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text(source)
            findings = [(f.lineno, f.code) for f in check_file(path)]
        self.assertEqual(
            [
                (2, "PY2-MODULE"),
                (3, "PY2-BOOL"),
                (3, "PY2-NEXT"),
                (7, "PY2-ITER"),
                (9, "PY2-NAME"),
            ],
            findings,
        )

    def test_extension_form_findings_are_tracked(self):
        """Bundled extensions migrate to the rule without blocking CI."""
        finding = Finding(
            Path(__file__).resolve().parents[2] / "extensions" / "tool.py",
            1,
            "FORM-NATIVE",
            "native form use",
        )
        self.assertTrue(_is_tracked_extension_finding(finding))


if __name__ == "__main__":
    unittest.main()
