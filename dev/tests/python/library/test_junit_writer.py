"""Tests for the JUnit XML reporter.

The reporter is loaded by path rather than imported, because it must stay importable
without a Revit host and `pyrevit.unittests` is a package that pulls in `pyrevit`.

Kept IronPython 2.7 compatible, apart from the `pytest` marker, so the same tests
can run on the default engine the reporter targets.

The shared runner discovers these API-free library fixtures separately from the
hosted suites in pyrevit.unittests.
"""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"


import io
import os
import tempfile
import types
import unittest
import pytest
from xml.etree import ElementTree

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 4))

JUNIT_PATH = os.path.join(
    REPO_ROOT,
    "pyrevitlib",
    "pyrevit",
    "unittests",
    "junit.py",
)


def _load_junit():
    module = types.ModuleType("pyrevit_junit_under_test")
    module.__file__ = JUNIT_PATH
    with io.open(JUNIT_PATH, encoding="utf-8") as source:
        exec(compile(source.read(), JUNIT_PATH, "exec"), module.__dict__)
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


@pytest.mark.regression
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

    def test_distinct_module_reports_are_aggregated(self):
        self._write_one("one", "a")
        self._write_one("two", "b")
        with open(self.target) as report_file:
            written = report_file.read()
        root = ElementTree.fromstring(written)
        self.assertEqual("testsuites", root.tag)
        self.assertEqual(["one", "two"], [suite.get("name") for suite in root])

    def test_repeating_a_module_replaces_its_previous_result(self):
        self._write_one("one", "a")
        self._write_one("two", "b")
        self._write_one("one", "c")
        root = ElementTree.parse(self.target).getroot()
        self.assertEqual(2, len(root))
        self.assertEqual(
            ["b", "c"], [case.get("name") for case in root.iter("testcase")]
        )

    def test_write_never_produces_several_roots(self):
        for name in ("one", "two", "three"):
            self._write_one(name, "t")
        with open(self.target) as report_file:
            content = report_file.read()
        self.assertEqual("testsuites", ElementTree.fromstring(content).tag)
        self.assertEqual(3, len(ElementTree.fromstring(content)))

    def test_interrupted_write_keeps_the_previous_report(self):
        self._write_one("one", "a")
        original = junit._serialize

        def interrupted(element):
            raise IOError("interrupted")

        junit._serialize = interrupted
        try:
            self.assertRaises(IOError, self._write_one, "two", "b")
        finally:
            junit._serialize = original
        root = ElementTree.parse(self.target).getroot()
        self.assertEqual("one", root.get("name"))

    def test_unparsable_report_is_reported_not_replaced(self):
        truncated = b"<testsuites><testsuite".decode("utf-8")
        os.makedirs(os.path.dirname(self.target))
        with io.open(self.target, "w", encoding="utf-8") as report_file:
            report_file.write(truncated)
        with self.assertRaises(ValueError) as raised:
            self._write_one("one", "a")
        self.assertIn(self.target, str(raised.exception))
        self.assertIn("delete", str(raised.exception))
        with io.open(self.target, encoding="utf-8") as report_file:
            self.assertEqual(truncated, report_file.read())

    def test_rewrite_without_os_replace(self):
        junit.os = _Python27Os()
        try:
            self._write_one("one", "a")
            self._write_one("two", "b")
        finally:
            junit.os = os
        root = ElementTree.parse(self.target).getroot()
        self.assertEqual(["one", "two"], [suite.get("name") for suite in root])
        self.assertFalse(os.path.exists(self.target + ".tmp"))


class _Python27Os(object):
    """os without `replace`, as on Python 2.7."""

    def __getattr__(self, name):
        if name == "replace":
            raise AttributeError(name)
        return getattr(os, name)


class _Python27ElementTree(object):
    """ElementTree whose tostring rejects the "unicode" encoding, as Python 2.7 does."""

    def __getattr__(self, name):
        return getattr(ElementTree, name)

    @staticmethod
    def tostring(element, encoding=None, method=None):
        if encoding == "unicode":
            raise LookupError("unknown encoding: unicode")
        return ElementTree.tostring(element, encoding=encoding, method=method)


class TestEncoding(unittest.TestCase):
    NON_ASCII = b"caf\xc3\xa9 \xc3\xbcber \xe6\x97\xa5\xe6\x9c\xac".decode("utf-8")

    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix="pyrevit-junit-enc-")
        self.target = os.path.join(self.directory, "report.xml")
        self.original = junit.ElementTree
        junit.ElementTree = _Python27ElementTree()

    def tearDown(self):
        junit.ElementTree = self.original

    def _report(self, name):
        report = junit.JUnitReport(name)
        report.add_failure(
            "test_" + self.NON_ASCII, self.NON_ASCII, trace=self.NON_ASCII
        )
        return report

    def test_to_xml_has_a_single_declaration(self):
        xml = self._report("one").to_xml()
        self.assertTrue(
            xml.startswith('<?xml version="1.0" encoding="utf-8"?><testsuite')
        )
        self.assertEqual(1, xml.count("<?xml"))

    def test_non_ascii_text_round_trips_through_write(self):
        self._report("one").write(self.target)
        self._report("two").write(self.target)
        with io.open(self.target, encoding="utf-8") as report_file:
            content = report_file.read()
        self.assertEqual(1, content.count("<?xml"))
        failure = (
            ElementTree.parse(self.target).getroot().find("testsuite/testcase/failure")
        )
        self.assertEqual(self.NON_ASCII, failure.get("message"))
        self.assertEqual(self.NON_ASCII, failure.text)


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
