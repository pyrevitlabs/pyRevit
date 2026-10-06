"""JUnit XML reporting for the in-Revit unit test suites.

The suites in this package run inside Revit and report to the output window, which CI
cannot read. This module renders the same outcomes as JUnit XML so a runner can upload
them and a reader gets failures inline in the job summary.

Deliberately free of pyrevit imports so a plain CPython test can load it without a
Revit host. Targets IronPython 2.7 as well as CPython 3, since 2.7 is the default engine.
"""

import os
import time
from xml.etree import ElementTree

DEFAULT_SUITE_NAME = "pyrevit.unittests"

PATH_ENV_VAR = "PYREVIT_TEST_JUNIT_PATH"


def _to_text(value):
    """Coerces a value to text without depending on a str/unicode split absent in py2."""
    try:
        return unicode(value)  # noqa: F821  (IronPython 2 / Python 2)
    except NameError:
        return str(value)


def _format_seconds(seconds):
    """Formats a duration as JUnit decimal seconds, clamping values consumers reject."""
    return "{0:.3f}".format(max(0.0, float(seconds)))


def report_path():
    """The configured report path, or None when reporting is off.

    Returns:
        str: path from `PATH_ENV_VAR`, or None.
    """
    path = os.environ.get(PATH_ENV_VAR)
    if not path or not path.strip():
        return None
    return path.strip()


class JUnitReport(object):
    """Accumulates test outcomes and renders them as a JUnit XML document.

    One report describes one `<testsuite>`. A suite that reports more than once appends,
    see `write`.

    Args:
        name (str): `<testsuite>` name. Defaults to `DEFAULT_SUITE_NAME`.
        timestamp (str): ISO-8601 suite stamp. Defaults to the current time.
    """

    def __init__(self, name=DEFAULT_SUITE_NAME, timestamp=None):
        self._name = name
        self._timestamp = timestamp or time.strftime("%Y-%m-%dT%H:%M:%S")
        self._test_cases = []
        self._duration = 0.0

    @property
    def name(self):
        """str: the `<testsuite>` name."""
        return self._name

    @property
    def total(self):
        """int: number of reported test cases."""
        return len(self._test_cases)

    def add_success(self, test_id, classname=None, duration=0.0):
        """Records a passing test.

        Args:
            test_id (str): test name as it should appear in a report.
            classname (str): suite or class the test belongs to.
            duration (float): seconds the test took.
        """
        self._add(test_id, classname, duration)

    def add_failure(self, test_id, message, trace=None, classname=None, duration=0.0):
        """Records a failing assertion.

        Args:
            test_id (str): test name.
            message (str): short reason.
            trace (str): traceback or detail.
            classname (str): suite or class the test belongs to.
            duration (float): seconds the test took.
        """
        self._add(
            test_id,
            classname,
            duration,
            kind="failure",
            message=message,
            detail=trace,
        )

    def add_error(self, test_id, message, trace=None, classname=None, duration=0.0):
        """Records a test that raised instead of failing an assertion.

        Args:
            test_id (str): test name.
            message (str): short summary.
            trace (str): traceback or detail.
            classname (str): suite or class the test belongs to.
            duration (float): seconds the test took.
        """
        self._add(
            test_id,
            classname,
            duration,
            kind="error",
            message=message,
            detail=trace,
        )

    def add_skipped(self, test_id, reason=None, classname=None, duration=0.0):
        """Records a skipped test.

        Args:
            test_id (str): test name.
            reason (str): why it was skipped.
            classname (str): suite or class the test belongs to.
            duration (float): seconds the test took.
        """
        self._add(
            test_id,
            classname,
            duration,
            kind="skipped",
            message=reason,
        )

    def _add(self, test_id, classname, duration, kind=None, message=None, detail=None):
        duration = max(0.0, float(duration or 0.0))
        self._duration += duration
        self._test_cases.append(
            {
                "id": _to_text(test_id),
                "classname": _to_text(classname) if classname else None,
                "duration": duration,
                "kind": kind,
                "message": message,
                "detail": detail,
            }
        )

    def to_xml(self):
        """Renders the report.

        Returns:
            str: XML document with an XML declaration.
        """
        testsuite = ElementTree.Element("testsuite")
        testsuite.set("name", self._name)
        testsuite.set("tests", str(len(self._test_cases)))
        testsuite.set("failures", str(self._count("failure")))
        testsuite.set("errors", str(self._count("error")))
        testsuite.set("skipped", str(self._count("skipped")))
        testsuite.set("time", _format_seconds(self._duration))
        testsuite.set("timestamp", self._timestamp)

        for case in self._test_cases:
            self._append_case(testsuite, case)

        declaration = '<?xml version="1.0" encoding="utf-8"?>'
        return declaration + ElementTree.tostring(testsuite, encoding="unicode")

    def _count(self, kind):
        """Number of recorded cases of one kind."""
        return len([case for case in self._test_cases if case["kind"] == kind])

    @staticmethod
    def _append_case(testsuite, case):
        element = ElementTree.SubElement(testsuite, "testcase")
        element.set("name", case["id"])
        element.set("classname", case["classname"] or DEFAULT_SUITE_NAME)
        element.set("time", _format_seconds(case["duration"]))

        if not case["kind"]:
            return

        if case["kind"] == "skipped":
            if case["message"]:
                element.set("message", _to_text(case["message"]))
            ElementTree.SubElement(element, "skipped")
            return

        child = ElementTree.SubElement(element, case["kind"])
        if case["message"]:
            child.set("message", _to_text(case["message"]))
        if case["detail"]:
            child.text = _to_text(case["detail"])
        elif case["message"]:
            child.text = _to_text(case["message"])

    def write(self, path=None):
        """Writes the report, replacing any previous file and creating parents as needed.

        Important: writes once per run. Writing per outcome would either lose earlier
        results or leave several root elements in the file, which no JUnit consumer
        accepts.

        Args:
            path (str): destination file. Defaults to `PATH_ENV_VAR`; when that is unset
                nothing is written and None is returned.

        Returns:
            str: the path written, or None when reporting is off.
        """
        if path is None:
            path = report_path()
        if path is None:
            return None

        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

        with open(path, "w") as report_file:
            report_file.write(self.to_xml())
            report_file.write("\n")

        return path
