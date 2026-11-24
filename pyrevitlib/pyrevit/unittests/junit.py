"""JUnit XML reporting for the in-Revit unit test suites.

The suites in this package run inside Revit and report to the output window, which CI
cannot read. This module renders the same outcomes as JUnit XML so a runner can upload
them and a reader gets failures inline in the job summary.

Deliberately free of pyrevit imports so a plain CPython test can load it without a
Revit host. Targets IronPython 2.7 as well as CPython 3, since 2.7 is the default engine.
"""

import io
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


def _serialize(element):
    """Serializes an element to text without an XML declaration.

    Note: Python 2.7 rejects `encoding="unicode"`; lower-case "utf-8" is the one
    encoding both 2.7 and 3 serialize without adding a declaration.
    """
    return ElementTree.tostring(element, encoding="utf-8").decode("utf-8")


def _format_seconds(seconds):
    """Formats a duration as JUnit decimal seconds, clamping values consumers reject."""
    return "{0:.3f}".format(max(0.0, float(seconds)))


def _replace(source, destination):
    """Moves a finished file over the destination.

    Note: IronPython 2.7 has no `os.replace` and its `os.rename` refuses an existing
    destination, so there the old file is removed first. A crash between the two
    steps loses the old report but never leaves a truncated one.
    """
    if hasattr(os, "replace"):
        os.replace(source, destination)
        return
    if os.path.exists(destination):
        os.remove(destination)
    os.rename(source, destination)


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

    One report describes one `<testsuite>`. Writing it replaces any earlier result for
    the same suite name and keeps the other suites in the file, see `write`.

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
        declaration = '<?xml version="1.0" encoding="utf-8"?>'
        return declaration + _serialize(self._testsuite())

    def _testsuite(self):
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
        return testsuite

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
        """Preserves other module suites while replacing this suite's previous result.

        Important: writes once per run. Writing per outcome would either lose earlier
        results or leave several root elements in the file, which no JUnit consumer
        accepts. Module runs sharing a destination must execute serially; give
        independent runs separate paths.

        Args:
            path (str): destination file. Defaults to `PATH_ENV_VAR`; when that is unset
                nothing is written and None is returned.

        Returns:
            str: the path written, or None when reporting is off.

        Raises:
            ValueError: the existing file is not a JUnit report. It is left in place,
                since starting over would drop the suites already reported to it.
        """
        if path is None:
            path = report_path()
        if path is None:
            return None

        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

        current = self._testsuite()
        suites = []
        if os.path.isfile(path):
            try:
                previous = ElementTree.parse(path).getroot()
            except ElementTree.ParseError as error:
                raise ValueError(
                    "JUnit report {0} is not valid XML ({1}); delete it and rerun".format(
                        path, error
                    )
                )
            if previous.tag == "testsuite":
                suites = [previous]
            elif previous.tag == "testsuites":
                suites = list(previous)
            else:
                raise ValueError("Expected a JUnit testsuite or testsuites root")
        suites = [suite for suite in suites if suite.get("name") != current.get("name")]
        suites.append(current)
        root = current
        if len(suites) > 1:
            root = ElementTree.Element("testsuites")
            for suite in suites:
                root.append(suite)
            for attribute in ("tests", "failures", "errors", "skipped"):
                root.set(
                    attribute,
                    str(sum(int(suite.get(attribute, "0")) for suite in suites)),
                )

        partial_path = path + ".tmp"
        with io.open(partial_path, "w", encoding="utf-8") as report_file:
            report_file.write(_to_text('<?xml version="1.0" encoding="utf-8"?>'))
            report_file.write(_serialize(root))
            report_file.write(_to_text("\n"))
        _replace(partial_path, path)

        return path
