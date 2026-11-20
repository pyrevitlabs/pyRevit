"""Exercise hosted runner failure contracts without importing the Revit host."""

import ast
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

REPO = Path(__file__).resolve().parents[4]
RUNNER = REPO / "pyrevitlib/pyrevit/unittests/runner.py"
RUN_ALL_SCRIPT = (
    REPO
    / "extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel"
    / "Unit Tests.pulldown/Run All Tests.pushbutton/script.py"
)


def _load_function(name, namespace):
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(RUNNER), "exec"),
        namespace,
    )
    return namespace[name]


@pytest.mark.regression
class RunnerFailureTests(unittest.TestCase):
    """A displayed success cannot hide an unexpected success or lost report."""

    def test_legacy_success_does_not_hide_unexpected_success(self):
        """IronPython's legacy wasSuccessful ignores unexpected successes."""
        result = SimpleNamespace(
            wasSuccessful=lambda: True,
            unexpectedSuccesses=["case"],
            failures=[],
            errors=[],
        )
        namespace = {"run_module_tests": lambda module: result}
        _load_function("was_successful", namespace)
        assertion = _load_function("assert_module_tests_successful", namespace)
        with self.assertRaisesRegex(AssertionError, "unexpected successes=1"):
            assertion(SimpleNamespace(__name__="fixture"))

    def test_run_all_button_fails_on_unexpected_success(self):
        """The Run All Tests button judges a module like the assertion does."""
        result = SimpleNamespace(
            wasSuccessful=lambda: True,
            unexpectedSuccesses=["case"],
            failures=[],
            errors=[],
            skipped=[],
        )
        runner = ModuleType("pyrevit.unittests.runner")
        runner.run_module_tests = lambda module: result
        _load_function("was_successful", runner.__dict__)
        with tempfile.TemporaryDirectory() as hosted_dir:
            Path(hosted_dir, "test_fixture.py").write_text("", encoding="utf-8")
            package = ModuleType("pyrevit.unittests")
            package.__path__ = [hosted_dir]
            package.runner = runner
            modules = {
                "pyrevit": ModuleType("pyrevit"),
                "pyrevit.unittests": package,
                "pyrevit.unittests.runner": runner,
                "pyrevit.unittests.test_fixture": ModuleType(
                    "pyrevit.unittests.test_fixture"
                ),
            }
            modules["pyrevit"].unittests = package
            with patch.dict(sys.modules, modules):
                with self.assertRaisesRegex(AssertionError, "test_fixture"):
                    exec(
                        compile(
                            RUN_ALL_SCRIPT.read_text(encoding="utf-8"),
                            str(RUN_ALL_SCRIPT),
                            "exec",
                        ),
                        {"__name__": "__main__"},
                    )

    def test_report_write_failure_is_propagated(self):
        """An explicitly requested report is required evidence."""
        namespace = {"mlogger": Mock()}
        stop = _load_function("stopTestRun", namespace)
        result_type = type(
            "PyRevitTestResult", (unittest.TestResult,), {"stopTestRun": stop}
        )
        namespace["PyRevitTestResult"] = result_type
        result = result_type()
        result._junit = SimpleNamespace(write=Mock(side_effect=OSError("cannot write")))
        with self.assertRaisesRegex(OSError, "cannot write"):
            result.stopTestRun()
