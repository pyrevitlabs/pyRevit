"""Exercise hosted runner failure contracts without importing the Revit host."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import pytest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

RUNNER = Path(__file__).resolve().parents[2] / "pyrevitlib/pyrevit/unittests/runner.py"


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
        assertion = _load_function(
            "assert_module_tests_successful",
            {"run_module_tests": lambda module: result},
        )
        with self.assertRaisesRegex(AssertionError, "unexpected successes=1"):
            assertion(SimpleNamespace(__name__="fixture"))

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
