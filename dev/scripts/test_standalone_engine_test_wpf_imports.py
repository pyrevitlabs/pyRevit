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


def _first_line(tree, predicate):
    lines = [node.lineno for node in ast.walk(tree) if predicate(node)]
    return min(lines) if lines else None


def _python_files():
    for root, _dirs, files in os.walk(PULLDOWN_DIR):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


def wpf_use_before_reference(source, filename="<script>"):
    """Return the line of the first unreferenced ``System.Windows`` use, or None."""
    tree = ast.parse(source, filename)
    use_line = _first_line(tree, _uses_system_windows)
    if use_line is None:
        return None
    reference_line = _first_line(tree, _references_wpf)
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
