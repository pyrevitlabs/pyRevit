"""Exercise hosted runner failure contracts without importing the Revit host."""

import ast
import io
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import pytest
from xml.etree import ElementTree

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

REPO = Path(__file__).resolve().parents[4]
RUNNER = REPO / "pyrevitlib/pyrevit/unittests/runner.py"
JUNIT = REPO / "pyrevitlib/pyrevit/unittests/junit.py"
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


def _expected_outcomes_case():
    class ExpectedOutcomes(unittest.TestCase):
        @unittest.expectedFailure
        def test_fails_as_expected(self):
            self.fail("known bug")

        @unittest.expectedFailure
        def test_passes_unexpectedly(self):
            pass

    return ExpectedOutcomes


def _run_with_report(path):
    junit = ModuleType("pyrevit.unittests.junit")
    junit.__file__ = str(JUNIT)
    with io.open(str(JUNIT), encoding="utf-8") as source:
        exec(compile(source.read(), str(JUNIT), "exec"), junit.__dict__)
    package = ModuleType("pyrevit.unittests")
    package.junit = junit
    logger = ModuleType("pyrevit.coreutils.logger")
    logger.get_logger = lambda name: Mock()
    output = ModuleType("pyrevit.output")
    output.get_output = lambda: Mock()
    modules = {
        "pyrevit": ModuleType("pyrevit"),
        "pyrevit.coreutils": ModuleType("pyrevit.coreutils"),
        "pyrevit.coreutils.logger": logger,
        "pyrevit.output": output,
        "pyrevit.unittests": package,
        "pyrevit.unittests.junit": junit,
    }
    runner = ModuleType("pyrevit.unittests.runner")
    with patch.dict(sys.modules, modules):
        with patch.dict(os.environ, {junit.PATH_ENV_VAR: path}):
            exec(
                compile(RUNNER.read_text(encoding="utf-8"), str(RUNNER), "exec"),
                runner.__dict__,
            )
            suite = unittest.TestLoader().loadTestsFromTestCase(
                _expected_outcomes_case()
            )
            result = runner.PyRevitTestRunner(suite_name="expected").run(suite)
    return runner, result


@pytest.mark.regression
class ExpectedOutcomeReportTests(unittest.TestCase):
    """The JUnit report agrees with was_successful on expected-failure outcomes."""

    def test_report_records_unexpected_success_as_failure(self):
        """An unexpected success is a failure element; an expected failure is skipped."""
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "report.xml")
            runner, result = _run_with_report(path)
            suite = ElementTree.parse(path).getroot().find("testsuite")
            if suite is None:
                suite = ElementTree.parse(path).getroot()
        cases = {case.get("name"): case for case in suite.iter("testcase")}
        unexpected = next(c for n, c in cases.items() if "passes_unexpectedly" in n)
        expected = next(c for n, c in cases.items() if "fails_as_expected" in n)
        self.assertIsNotNone(unexpected.find("failure"))
        self.assertIsNotNone(expected.find("skipped"))
        self.assertFalse(runner.was_successful(result))
        self.assertEqual(suite.get("failures"), "1")
        self.assertEqual(suite.get("skipped"), "1")
