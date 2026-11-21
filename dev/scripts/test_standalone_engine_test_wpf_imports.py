"""Host-free checks that Engine Tests scripts load WPF before using it.

A fresh IronPython engine has no reference to the WPF assemblies, so
``from System import Windows`` fails with ``Cannot import name Windows``
unless ``pyrevit.framework`` or ``clr.AddReference`` loaded them first.
"""

import ast
import os
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

WPF_ASSEMBLIES = (
    "PresentationFramework",
    "PresentationCore",
    "WindowsBase",
    "IronPython.Wpf",
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PULLDOWN_DIR = os.path.join(
    REPO_ROOT,
    "extensions",
    "pyRevitDevTools.extension",
    "pyRevitDev.tab",
    "Debug.panel",
    "Engine Tests.pulldown",
)


def _dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _uses_system_windows(node):
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module == "System":
            return any(alias.name == "Windows" for alias in node.names)
        return module.startswith("System.Windows")
    if isinstance(node, ast.Import):
        return any(alias.name.startswith("System.Windows") for alias in node.names)
    if isinstance(node, ast.Attribute):
        return _dotted_name(node) == "System.Windows"
    return False


def _references_wpf(node):
    if isinstance(node, ast.ImportFrom):
        if node.module == "pyrevit.framework":
            return True
        return node.module == "pyrevit" and any(
            alias.name == "framework" for alias in node.names
        )
    if isinstance(node, ast.Import):
        return any(alias.name == "pyrevit.framework" for alias in node.names)
    if isinstance(node, ast.Call) and _dotted_name(node.func) == "clr.AddReference":
        return any(
            isinstance(arg, ast.Constant) and arg.value in WPF_ASSEMBLIES
            for arg in node.args
        )
    return False


_DEFERRED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _definition_time_nodes(scope):
    args = scope.args
    return (
        getattr(scope, "decorator_list", [])
        + args.defaults
        + [default for default in args.kw_defaults if default is not None]
    )


def _live_children(node):
    if isinstance(node, ast.If) and isinstance(node.test, ast.Constant):
        children = [node.test] + (node.body if node.test.value else node.orelse)
    else:
        children = ast.iter_child_nodes(node)
    live = []
    for child in children:
        if isinstance(child, _DEFERRED_SCOPES):
            live.extend(_definition_time_nodes(child))
        else:
            live.append(child)
    return live


def _import_time_nodes(tree):
    pending = [tree]
    while pending:
        node = pending.pop()
        yield node
        pending.extend(_live_children(node))


def _first_line(nodes, predicate):
    lines = [node.lineno for node in nodes if predicate(node)]
    return min(lines) if lines else None


def _python_files():
    for root, _dirs, files in os.walk(PULLDOWN_DIR):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


def wpf_use_before_reference(source, filename="<script>"):
    """Return the line of the first unreferenced ``System.Windows`` use, or None.

    Note:
        Only code that runs at import time is compared. Function and lambda
        bodies are ignored, wherever they are defined, because they run only
        when called; their decorators and default values still count. So a
        use inside a function called before the load is not flagged. Branches
        of an ``if`` whose test is a literal constant (``if False:``,
        ``if 0:``, the ``else`` of ``if True:``) are ignored; other dead
        conditions are not detected. Other blocks such as ``try`` count.
    """
    tree = ast.parse(source, filename)
    nodes = list(_import_time_nodes(tree))
    use_line = _first_line(nodes, _uses_system_windows)
    if use_line is None:
        return None
    reference_line = _first_line(nodes, _references_wpf)
    if reference_line is not None and reference_line < use_line:
        return None
    return use_line


class WpfUseBeforeReferenceTests(unittest.TestCase):
    def test_bare_system_windows_import_is_flagged(self):
        self.assertEqual(wpf_use_before_reference("from System import Windows\n"), 1)

    def test_framework_import_before_use_is_accepted(self):
        source = "from pyrevit import framework\nfrom System import Windows\n"
        self.assertIsNone(wpf_use_before_reference(source))

    def test_add_reference_before_use_is_accepted(self):
        source = (
            "import clr\n"
            "clr.AddReference('PresentationFramework')\n"
            "import System\n"
            "System.Windows.Window()\n"
        )
        self.assertIsNone(wpf_use_before_reference(source))

    def test_non_wpf_add_reference_is_flagged(self):
        source = (
            "import clr\nclr.AddReference('RevitAPI')\nfrom System import Windows\n"
        )
        self.assertEqual(wpf_use_before_reference(source), 3)

    def test_framework_import_after_use_is_flagged(self):
        source = "from System import Windows\nfrom pyrevit.framework import wpf\n"
        self.assertEqual(wpf_use_before_reference(source), 1)

    def test_framework_import_in_uncalled_function_is_flagged(self):
        source = (
            "def helper():\n"
            "    from pyrevit.framework import Windows\n"
            "from System import Windows\n"
        )
        self.assertEqual(wpf_use_before_reference(source), 3)

    def test_use_in_function_called_after_framework_import_is_accepted(self):
        source = (
            "def show():\n"
            "    from System import Windows\n"
            "from pyrevit import framework\n"
            "show()\n"
        )
        self.assertIsNone(wpf_use_before_reference(source))

    def test_framework_import_in_inactive_branch_is_flagged(self):
        source = (
            "if False:\n    from pyrevit import framework\nfrom System import Windows\n"
        )
        self.assertEqual(wpf_use_before_reference(source), 3)

    def test_framework_import_in_try_block_is_accepted(self):
        source = (
            "try:\n"
            "    from pyrevit import framework\n"
            "except ImportError:\n"
            "    pass\n"
            "from System import Windows\n"
        )
        self.assertIsNone(wpf_use_before_reference(source))

    def test_framework_import_in_function_inside_active_branch_is_flagged(self):
        source = (
            "if True:\n"
            "    def helper():\n"
            "        from pyrevit import framework\n"
            "from System import Windows\n"
        )
        self.assertEqual(wpf_use_before_reference(source), 4)

    def test_use_in_default_argument_is_flagged(self):
        source = (
            "import System\ndef show(window_type=System.Windows.Window):\n    pass\n"
        )
        self.assertEqual(wpf_use_before_reference(source), 2)


class EngineTestsScriptsTests(unittest.TestCase):
    def test_scripts_reference_wpf_before_using_system_windows(self):
        offenders = []
        for path in _python_files():
            with open(path, encoding="utf-8") as script_file:
                line = wpf_use_before_reference(script_file.read(), path)
            if line is not None:
                offenders.append("{}:{}".format(os.path.relpath(path, REPO_ROOT), line))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
