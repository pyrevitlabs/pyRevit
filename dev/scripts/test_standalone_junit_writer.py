"""Tests for the JUnit XML reporter.

The reporter is loaded by path rather than imported, because it must stay importable
without a Revit host and `pyrevit.unittests` is a package that pulls in `pyrevit`.

That host-free requirement is why these suites sit here instead of beside the code
they cover: every test in `pyrevitlib/pyrevit/unittests/` imports `pyrevit` and needs
Revit to run, so a suite that has to gate CI cannot live there. CI discovers them with
`-p 'test_standalone_*.py'`; the other `test_*.py` files in this folder cover
`dev/scripts` tooling and are run through the `pipenv run test-*` scripts.
"""

import importlib.util
import os
import tempfile
import unittest
from xml.etree import ElementTree

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

JUNIT_PATH = os.path.join(
    REPO_ROOT,
    "pyrevitlib",
    "pyrevit",
    "unittests",
    "junit.py",
)


def _load_junit():
    spec = importlib.util.spec_from_file_location(
        "pyrevit_junit_under_test", JUNIT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


junit = _load_junit()


def _mixed_report():
    report = junit.JUnitReport(
        "pyrevit.unittests.demo", timestamp="2026-10-05T00:00:00"
    )
    report.add_success("test_ok", classname="DemoCase", duration=0.25)
    report.add_failure(
        "test_bad",
        "AssertionError: 1 != 2",
        trace="Traceback (most recent call last):\n  assert 1 == 2",
        classname="DemoCase",
        duration=0.5,
    )
    report.add_error(
        "test_boom",
        "RuntimeError: kaboom",
        trace="Traceback ...\nRuntimeError: kaboom",
        classname="DemoCase",
        duration=1.0,
    )
    report.add_skipped("test_skip", "needs Revit 2026", classname="DemoCase")
    return report


class TestSuiteAttributes(unittest.TestCase):
    def setUp(self):
        self.root = ElementTree.fromstring(_mixed_report().to_xml())

    def test_root_is_a_testsuite(self):
        self.assertEqual("testsuite", self.root.tag)

    def test_suite_identity_is_carried_through(self):
        self.assertEqual("pyrevit.unittests.demo", self.root.get("name"))
        self.assertEqual("2026-10-05T00:00:00", self.root.get("timestamp"))

    def test_counts_match_recorded_cases(self):
        self.assertEqual("4", self.root.get("tests"))
        self.assertEqual("1", self.root.get("failures"))
        self.assertEqual("1", self.root.get("errors"))
        self.assertEqual("1", self.root.get("skipped"))

    def test_suite_time_is_the_sum_of_durations(self):
        self.assertEqual("1.750", self.root.get("time"))


class TestCaseElements(unittest.TestCase):
    def setUp(self):
        self.cases = ElementTree.fromstring(_mixed_report().to_xml()).findall(
            "testcase"
        )

    def test_every_recorded_case_is_written(self):
        self.assertEqual(
            ["test_ok", "test_bad", "test_boom", "test_skip"],
            [case.get("name") for case in self.cases],
        )

    def test_classname_is_carried_through(self):
        self.assertTrue(all(case.get("classname") == "DemoCase" for case in self.cases))

    def test_passing_case_has_no_child(self):
        self.assertEqual(0, len(self.cases[0]))

    def test_failure_carries_message_and_traceback(self):
        failure = self.cases[1].find("failure")
        self.assertIsNotNone(failure)
        self.assertEqual("AssertionError: 1 != 2", failure.get("message"))
        self.assertIn("assert 1 == 2", failure.text)

    def test_error_is_distinct_from_failure(self):
        error = self.cases[2].find("error")
        self.assertIsNotNone(error)
        self.assertIsNone(self.cases[2].find("failure"))
        self.assertEqual("RuntimeError: kaboom", error.get("message"))

    def test_skip_reason_travels_on_the_testcase(self):
        self.assertIsNotNone(self.cases[3].find("skipped"))
        self.assertEqual("needs Revit 2026", self.cases[3].get("message"))


class TestDocumentWellFormedness(unittest.TestCase):
    def test_declaration_is_present(self):
        self.assertTrue(
            _mixed_report()
            .to_xml()
            .startswith('<?xml version="1.0" encoding="utf-8"?>')
        )

    def test_markup_in_a_traceback_round_trips(self):
        report = junit.JUnitReport("escape")
        report.add_failure("test_xml", "bad <input> & worse", trace="a < b && c > d")
        failure = ElementTree.fromstring(report.to_xml()).find("testcase/failure")
        self.assertEqual("a < b && c > d", failure.text)

    def test_negative_duration_is_clamped(self):
        report = junit.JUnitReport("odd")
        report.add_success("x", duration=-5.0)
        self.assertEqual("0.000", ElementTree.fromstring(report.to_xml()).get("time"))

    def test_unnamed_case_falls_back_to_the_default_classname(self):
        report = junit.JUnitReport("named")
        report.add_success("x")
        self.assertEqual(
            junit.DEFAULT_SUITE_NAME,
            ElementTree.fromstring(report.to_xml()).find("testcase").get("classname"),
        )


class TestWriting(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="pyrevit-junit-")
        self.target = os.path.join(self.directory, "nested", "report.xml")

    def _write_one(self, name, test_id):
        report = junit.JUnitReport(name)
        report.add_success(test_id)
        return report.write(self.target)

    def test_write_creates_missing_parent_directories(self):
        self.assertTrue(os.path.isfile(self._write_one("one", "a")))

    def test_a_second_run_replaces_the_first(self):
        self._write_one("one", "a")
        self._write_one("two", "b")
        with open(self.target) as report_file:
            written = report_file.read()
        self.assertEqual(1, written.count("<testsuite"))
        self.assertEqual("1", ElementTree.fromstring(written).get("tests"))

    def test_write_never_produces_several_roots(self):
        for name in ("one", "two", "three"):
            self._write_one(name, "t")
        with open(self.target) as report_file:
            content = report_file.read()
        self.assertEqual(1, content.count("<testsuite"))
        self.assertEqual(1, content.count("</testsuite>"))


class TestEnvironmentEntryPoint(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="pyrevit-junit-env-")
        self.target = os.path.join(self.directory, "env.xml")
        self.previous = os.environ.get(junit.PATH_ENV_VAR)
        os.environ[junit.PATH_ENV_VAR] = self.target

    def tearDown(self):
        if self.previous is None:
            del os.environ[junit.PATH_ENV_VAR]
        else:
            os.environ[junit.PATH_ENV_VAR] = self.previous

    def test_report_path_reflects_the_environment(self):
        self.assertEqual(self.target, junit.report_path())

    def test_write_defaults_to_the_environment_path(self):
        report = junit.JUnitReport("envsuite")
        report.add_success("envtest", duration=0.1)
        written = report.write()
        self.assertEqual(self.target, written)
        self.assertEqual("envsuite", ElementTree.parse(written).getroot().get("name"))

    def test_every_outcome_survives_a_single_write(self):
        report = junit.JUnitReport("kinds")
        report.add_success("t")
        report.add_failure("f", "AssertionError: x", trace="tb")
        report.add_error("e", "RuntimeError: y", trace="tb")
        report.add_skipped("s", "later")
        written = report.write()
        root = ElementTree.parse(written).getroot()
        self.assertEqual("4", root.get("tests"))
        self.assertEqual(
            ("1", "1", "1"),
            (root.get("failures"), root.get("errors"), root.get("skipped")),
        )


class TestReportingIsOptIn(unittest.TestCase):
    def tearDown(self):
        os.environ.pop(junit.PATH_ENV_VAR, None)

    def test_no_path_means_no_report(self):
        os.environ.pop(junit.PATH_ENV_VAR, None)
        self.assertIsNone(junit.report_path())

    def test_write_does_nothing_when_unconfigured(self):
        os.environ.pop(junit.PATH_ENV_VAR, None)
        self.assertIsNone(junit.JUnitReport("suite").write())

    def test_blank_path_is_treated_as_off(self):
        os.environ[junit.PATH_ENV_VAR] = "   "
        self.assertIsNone(junit.report_path())


if __name__ == "__main__":
    unittest.main()
