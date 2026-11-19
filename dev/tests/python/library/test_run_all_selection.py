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
OWN_BUTTON_MODULES = {
    "test_config_roundtrip",
    "test_create_view_helpers",
    "test_dynamo_execution",
    "test_forms_parity",
    "test_revit_api_catalog",
    "test_ribbon_control_ids",
}


def _selected_modules():
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
    return namespace["_discover_test_modules"]()


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
        self.selected = _selected_modules()

    def test_every_module_without_its_own_button_is_selected(self):
        """Only modules with their own entry point are left out."""
        self.assertTrue(OWN_BUTTON_MODULES <= self.hosted)
        self.assertEqual(sorted(self.hosted - OWN_BUTTON_MODULES), self.selected)

    def test_integration_module_is_selected(self):
        """An Integration level does not drop a module from the run."""
        self.assertEqual("Integration", _level("test_credentials"))
        self.assertIn("test_credentials", self.selected)
        self.assertNotIn("TEST_LEVEL", RUN_ALL_SCRIPT.read_text(encoding="utf-8"))

    def test_unit_module_is_selected(self):
        """A Unit module is run."""
        self.assertEqual("Unit", _level("test_context_conditions"))
        self.assertIn("test_context_conditions", self.selected)

    def test_opt_out_module_is_excluded(self):
        """Modules with their own entry point are not run."""
        self.assertNotIn("test_revit_api_catalog", self.selected)
        self.assertNotIn("test_dynamo_execution", self.selected)
