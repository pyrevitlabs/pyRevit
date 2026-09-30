"""Exercise production host accessors without importing Revit-dependent modules.

Only the selected production definitions are compiled; their dependencies use
small host doubles. This keeps None and missing-builtin tests isolated from the
process-wide builtins used by live engines.
"""

import ast
import io
import os
import unittest

try:
    import builtins
except ImportError:
    import __builtin__ as builtins


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class _Namespace(object):
    def __init__(self, **values):
        self.__dict__.update(values)


SimpleNamespace = _Namespace


def _source(relative_path):
    with io.open(os.path.join(ROOT, relative_path), encoding="utf-8-sig") as source:
        return source.read()


def _load(relative_path, names, namespace):
    isolated_builtins = dict(builtins.__dict__)
    for name in ("__revit__", "__scriptruntime__", "__eventargs__", "__eventsender__"):
        isolated_builtins.pop(name, None)
    namespace["__builtins__"] = isolated_builtins
    tree = ast.parse(_source(relative_path))
    tree.body = [node for node in tree.body if getattr(node, "name", None) in names]
    exec(compile(tree, relative_path, "exec"), namespace)
    return namespace


class _Application(object):
    VersionNumber = "2025"
    ActiveAddInId = "test-addin"


class _UIApplication(object):
    Application = _Application()
    ActiveUIDocument = SimpleNamespace(Document="document", ActiveView="view")


class _UnavailableDocument(_UIApplication):
    @property
    def ActiveUIDocument(self):
        raise RuntimeError("UI document unavailable during DB event")


class HostHandleTests(unittest.TestCase):
    """Cover defined, missing, legacy and event-limited host handles."""

    def setUp(self):
        """Load fresh production definitions for every test."""
        self.scope = _load(
            "pyrevitlib/pyrevit/__init__.py",
            {"_HostApplication", "_ExecutorParams", "_DocsGetter"},
            {
                "UI": SimpleNamespace(UIApplication=_UIApplication),
                "ApplicationServices": SimpleNamespace(Application=_Application),
            },
        )
        self.host = self.scope["_HostApplication"]()
        self.scope["HOST_APP"] = self.host
        self.scope["EXEC_PARAMS"] = self.scope["_ExecutorParams"]()

    def test_missing_builtin(self):
        """Absent handles preserve the safe accessor subset."""
        for name in ("uiapp", "app", "uidoc", "doc", "active_view", "docs"):
            self.assertIsNone(getattr(self.host, name), name)

    def test_null_builtin(self):
        """A defined None behaves like a missing builtin."""
        self.scope["__revit__"] = None
        self.test_missing_builtin()

    def test_live_ui_handle(self):
        """UI accessors and application metadata follow the injected handle."""
        handle = _UIApplication()
        self.scope["__revit__"] = handle
        self.assertIs(self.host.uiapp, handle)
        self.assertIs(self.host.app, handle.Application)
        self.assertEqual(self.host.doc, "document")
        self.assertEqual(self.host.active_view, "view")
        self.assertEqual(self.host.version, "2025")
        self.assertEqual(self.host.addin_id, "test-addin")

    def test_legacy_application(self):
        """Third-party DB handles retain application access without UI access."""
        self.scope["__revit__"] = _Application()
        self.assertIsNone(self.host.uiapp)
        self.assertIsNone(self.host.doc)
        self.assertEqual(self.host.version, "2025")

    def test_handle_is_read_again(self):
        """Cached Python modules observe the next execution's builtin."""
        self.scope["__revit__"] = _UIApplication()
        self.assertIsNotNone(self.host.uiapp)
        self.scope["__revit__"] = None
        self.assertIsNone(self.host.uiapp)

    def test_db_event_document_refusal(self):
        """API exceptions degrade UI-document access without losing the app."""
        self.scope["__revit__"] = _UnavailableDocument()
        self.assertIsNotNone(self.host.app)
        for name in ("uidoc", "doc", "active_view"):
            self.assertIsNone(getattr(self.host, name))

    def test_event_document_property_fallback(self):
        """DB event arguments provide the document when the UI cannot."""
        self.scope["__revit__"] = _UnavailableDocument()
        self.scope["__scriptruntime__"] = SimpleNamespace(
            ScriptRuntimeConfigs=SimpleNamespace(
                EventArgs=SimpleNamespace(Document="event-document")
            )
        )
        self.assertEqual(self.scope["_DocsGetter"]().doc, "event-document")

    def test_event_document_method_fallback(self):
        """DocumentChanged-style GetDocument arguments remain reachable."""
        self.scope["__revit__"] = None
        self.scope["__scriptruntime__"] = SimpleNamespace(
            ScriptRuntimeConfigs=SimpleNamespace(
                EventArgs=SimpleNamespace(GetDocument=lambda: "changed-document")
            )
        )
        self.assertEqual(self.scope["_DocsGetter"]().doc, "changed-document")

    def test_none_metadata_is_safe(self):
        """Metadata returns None and version comparisons return False without a host."""
        self.scope["__revit__"] = None
        for name in (
            "version",
            "addin_id",
            "username",
            "subversion",
            "version_name",
            "language",
            "pretty_name",
            "proc_window",
            "proc_screen",
        ):
            self.assertIsNone(getattr(self.host, name))
        self.assertFalse(self.host.has_api_context)
        self.assertFalse(self.host.is_newer_than(2025))
        self.assertFalse(self.host.is_older_than(2025))
        self.assertFalse(self.host.is_exactly(2025))
        self.assertEqual(self.host.available_servers, [])
        self.assertEqual(self.host.get_postable_commands(), [])


class VersionHandleTests(unittest.TestCase):
    """Cover compatibility version dispatch independently of CLR imports."""

    def test_all_supported_shapes(self):
        """UI, DB, controlled, unknown, missing and None handles dispatch safely."""
        scope = _load(
            "pyrevitlib/pyrevit/compat.py", {"_get_revit_version"}, {"NO_REVIT": -1}
        )
        self.assertEqual(scope["_get_revit_version"](), -1)
        for handle, expected in (
            (None, -1),
            (object(), -1),
            (_UIApplication(), 2025),
            (_Application(), 2025),
            (SimpleNamespace(ControlledApplication=_Application()), 2025),
        ):
            scope["__revit__"] = handle
            self.assertEqual(scope["_get_revit_version"](), expected)


class RpwHandleTests(unittest.TestCase):
    """Cover RPW fallback and document safety without loading its import graph."""

    def setUp(self):
        """Compile the production wrapper with inert external dependencies."""
        self.scope = _load(
            "pyrevitlib/rpw/__revit.py",
            {"Revit", "RevitVersion"},
            {
                "BaseObject": object,
                "logger": SimpleNamespace(warning=lambda message: None),
            },
        )
        self.wrapper = object.__new__(self.scope["Revit"])

    def test_null_and_missing_use_dynamo(self):
        """Missing pyRevit handles do not suppress the Dynamo fallback."""
        handle = _UIApplication()
        self.wrapper.find_dynamo_uiapp = lambda: handle
        self.assertIs(self.wrapper.find_uiapp(), handle)
        self.scope["__revit__"] = None
        self.assertIs(self.wrapper.find_uiapp(), handle)
        self.assertEqual(self.wrapper.host, "Dynamo")

    def test_live_handle_precedes_dynamo(self):
        """The injected handle wins over an available Dynamo handle."""
        handle = _UIApplication()
        self.scope["__revit__"] = handle
        self.wrapper.find_dynamo_uiapp = lambda: None
        self.assertIs(self.wrapper.find_uiapp(), handle)
        self.assertEqual(self.wrapper.host, "RPS")

    def test_missing_dynamo_is_safe(self):
        """Unavailable fallback reports no host."""

        def fail():
            raise RuntimeError("No Dynamo")

        self.wrapper.find_dynamo_uiapp = fail
        self.assertIsNone(self.wrapper.find_uiapp())
        self.assertIsNone(self.wrapper.host)

    def test_none_and_refused_document(self):
        """Both absent and event-limited UI handles yield no document."""
        for handle in (None, _UnavailableDocument()):
            self.wrapper.uiapp = handle
            self.assertIsNone(self.wrapper.uidoc)
            self.assertIsNone(self.wrapper.doc)

    def test_live_document(self):
        """The active document remains available for command execution."""
        self.wrapper.uiapp = _UIApplication()
        self.assertEqual(self.wrapper.doc, "document")

    def test_cached_handle_follows_reinjection(self):
        """Cached RPW instances follow new and null builtins."""
        old_handle = _UIApplication()
        self.wrapper._host = "RPS"
        self.wrapper.uiapp = old_handle
        self.scope["__revit__"] = _UIApplication()
        self.assertIsNot(self.wrapper.uiapp, old_handle)
        self.assertIs(self.wrapper.uiapp, self.scope["__revit__"])
        self.scope["__revit__"] = None
        self.assertIsNone(self.wrapper.uiapp)
        self.assertIsNone(self.wrapper.app)
        self.assertIsNone(self.wrapper.username)
        self.assertIsNone(self.wrapper.version)
        self.assertIsNone(self.wrapper.active_view)
        self.assertEqual(self.wrapper.docs, [])

    def test_sphinx_compat_import_without_imp(self):
        """The compatibility module imports on Python versions without imp."""
        source_path = "pyrevitlib/rpw/utils/sphinx_compat.py"
        tree = ast.parse(_source(source_path))
        tree.body = [
            node
            for node in tree.body
            if not (
                isinstance(node, ast.ImportFrom) and node.module == "rpw.utils.logger"
            )
        ]
        scope = {"logger": SimpleNamespace(debug=lambda message: None)}
        exec(compile(tree, str(source_path), "exec"), scope)
        mock = scope["MockObject"](fullname="RevitAPI")
        self.assertEqual(str(mock), "RevitAPI")

    def test_forms_environment_members_are_class_attributes(self):
        """Python.NET resolves Environment as a CLR type, not a module."""
        source_path = "pyrevitlib/rpw/ui/forms/resources.py"
        tree = ast.parse(_source(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "System.Environment")
        tree.body = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id in ("Exit", "NewLine")
                for target in node.targets
            )
        ]
        environment = SimpleNamespace(Exit=lambda code: None, NewLine="\r\n")
        scope = {"Environment": environment}
        exec(compile(tree, str(source_path), "exec"), scope)
        self.assertIs(scope["Exit"], environment.Exit)
        self.assertEqual(scope["NewLine"], "\r\n")

    def test_cpython_ui_import_does_not_load_ironpython_forms(self):
        """RPW host imports avoid forms that Python.NET cannot construct."""
        source_path = "pyrevitlib/rpw/ui/__init__.py"
        tree = ast.parse(_source(source_path))
        tree.body = [
            node
            for node in tree.body
            if not (
                isinstance(node, ast.ImportFrom) and node.module == "rpw.ui.selection"
            )
            and not isinstance(node, ast.Import)
        ]
        scope = {"platform": SimpleNamespace(python_implementation=lambda: "CPython")}
        exec(compile(tree, str(source_path), "exec"), scope)
        self.assertNotIn("forms", scope)
        with self.assertRaises(NotImplementedError):
            scope["__getattr__"]("forms")


if __name__ == "__main__":
    unittest.main(verbosity=2)
