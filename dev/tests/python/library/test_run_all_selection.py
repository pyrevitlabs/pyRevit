"""Check which hosted modules the DevTools Run All Tests button selects."""

import ast
from pathlib import Path
import pkgutil
from types import SimpleNamespace
import unittest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

REPO = Path(__file__).resolve().parents[4]
HOSTED_DIR = REPO / "pyrevitlib/pyrevit/unittests"
RUN_ALL_SCRIPT = (
    REPO
    / "extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel"
    / "Unit Tests.pulldown/Run All Tests.pushbutton/script.py"
)


def _button_namespace():
    tree = ast.parse(RUN_ALL_SCRIPT.read_text(encoding="utf-8"))
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        or (isinstance(node, ast.FunctionDef) and node.name == "_discover_test_modules")
    ]
    namespace = {
        "pkgutil": pkgutil,
        "tests_pkg": SimpleNamespace(__path__=[str(HOSTED_DIR)]),
    }
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), str(RUN_ALL_SCRIPT), "exec"),
        namespace,
    )
    return namespace


def _level(module_name):
    source = (HOSTED_DIR / (module_name + ".py")).read_text(encoding="utf-8")
    return next(
        ast.literal_eval(node.value)
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", None) == "TEST_LEVEL" for target in node.targets)
    )


class RunAllSelectionTests(unittest.TestCase):
    """Run All Tests selects by name, not by TEST_LEVEL."""

    def setUp(self):
        """Read the hosted modules on disk and the button's selection."""
        self.hosted = {path.stem for path in HOSTED_DIR.glob("test_*.py")}
        button = _button_namespace()
        self.opt_in = set(button["OPT_IN_MODULES"])
        self.selected = button["_discover_test_modules"]()

    def test_every_module_without_its_own_button_is_selected(self):
        """Only modules with their own entry point are left out."""
        self.assertTrue(self.opt_in <= self.hosted)
        self.assertEqual(sorted(self.hosted - self.opt_in), self.selected)

    def test_integration_modules_are_selected(self):
        """A level other than Unit does not drop a module from the run."""
        non_unit = {
            name for name in self.hosted - self.opt_in if _level(name) != "Unit"
        }
        self.assertTrue(non_unit)
        self.assertTrue(non_unit <= set(self.selected))
        self.assertNotIn("TEST_LEVEL", RUN_ALL_SCRIPT.read_text(encoding="utf-8"))
