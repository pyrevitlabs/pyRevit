"""Unit tests facility."""

import time
from unittest import TestResult, TestLoader
from xml.sax.saxutils import escape

from pyrevit.coreutils.logger import get_logger
from pyrevit.output import get_output
from pyrevit.unittests import junit


# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


DEBUG_OKAY_RESULT = "PASSED"
DEBUG_FAIL_RESULT = "FAILED"

RESULT_TEST_SUITE_START = (
    '<div class="unittest unitteststart">Test Suite: {suite}</div>'
)

RESULT_DIV_OKAY = (
    '<div class="unittest unittestokay">:white_heavy_check_mark: PASSED {test}</div>'
)

RESULT_DIV_FAIL = '<div class="unittest unittestfail">:cross_mark: FAILED {test}</div>'

RESULT_DIV_ERROR = (
    '<div class="unittest unittesterror">:heavy_large_circle: ERROR {test}</div>'
)


def _exception_summary(err):
    """Renders the exception type and message of a failure.

    Args:
        err (OptExcInfo): test exception info

    Returns:
        (str): short one-line reason, for the report's message attribute.
    """
    try:
        exc_type, exc_value = err[0], err[1]
        return "{0}: {1}".format(getattr(exc_type, "__name__", exc_type), exc_value)
    except Exception:
        return repr(err)


class OutputWriter:
    """Output writer for tests results."""

    def __init__(self):
        self._output = get_output()

    def write(self, output_str):
        """Prints the results to the output window.

        Args:
            output_str (str): Text to output
        """
        self._output.print_html(output_str)


class PyRevitTestResult(TestResult):
    """Pyrevit Test Result.

    Also writes JUnit XML when :data:`pyrevit.unittests.junit.PATH_ENV_VAR` is set, so
    the same run that reports to the output window can be read by CI. Reporting is off
    unless that variable is set, so running tests by hand leaves no files behind.

    Args:
        verbosity (int): verbosity level.
        suite_name (str): suite name for the report. Defaults to the runner's.
    """

    def __init__(self, verbosity, suite_name=None):
        super(PyRevitTestResult, self).__init__(verbosity=verbosity)
        self.writer = OutputWriter()
        self.suite_name = suite_name or junit.DEFAULT_SUITE_NAME
        self._junit = junit.JUnitReport(name=self.suite_name)
        self._started = {}

    @staticmethod
    def getDescription(test):
        """Returns the description of the test.

        Args:
            test (TestCase): Unit test.

        Returns:
            (str): test description
        """
        return test.shortDescription() or test

    @staticmethod
    def _classname(test):
        """The class a test belongs to, for the report.

        Args:
            test (TestCase): Unit test.

        Returns:
            (str): class name, or None for a module-level test.
        """
        return getattr(test, "__class__", type(test)).__name__

    def _duration(self, test):
        """Seconds a test took, 0.0 when the start time was never recorded.

        Args:
            test (TestCase): Unit test.

        Returns:
            (float): elapsed seconds.
        """
        started = self._started.pop(id(test), None)
        if started is None:
            return 0.0
        return time.time() - started

    def _report(self, kind, test, message=None, detail=None):
        """Accumulates one outcome in the JUnit report.

        Args:
            kind (str): success, failure, error or skipped.
            test (TestCase): Unit test.
            message (str): failure or skip reason.
            detail (str): traceback or failure detail.
        """
        if kind == "failure":
            self._junit.add_failure(
                self.getDescription(test),
                message,
                detail,
                classname=self._classname(test),
                duration=self._duration(test),
            )
        elif kind == "error":
            self._junit.add_error(
                self.getDescription(test),
                message,
                detail,
                classname=self._classname(test),
                duration=self._duration(test),
            )
        elif kind == "skipped":
            self._junit.add_skipped(
                self.getDescription(test),
                reason=message,
                classname=self._classname(test),
                duration=self._duration(test),
            )
        else:
            self._junit.add_success(
                self.getDescription(test),
                classname=self._classname(test),
                duration=self._duration(test),
            )

    def stopTestRun(self):
        """Writes the JUnit report, when one is configured.

        The whole report goes out in one file here rather than per test, so the result is
        a single well-formed document. Reporting is off unless
        `junit.PATH_ENV_VAR` is set, so running tests by hand leaves no files behind.
        """
        stop_test_run = getattr(super(PyRevitTestResult, self), "stopTestRun", None)
        if stop_test_run is not None:
            stop_test_run()

        try:
            written = self._junit.write()
            if written:
                mlogger.debug("Wrote JUnit report: %s", written)
        except Exception as report_error:
            mlogger.warning("Could not write JUnit report: %s", report_error)

    def startTest(self, test):
        """Starts the test.

        Args:
            test (TestCase): unit test
        """
        super(PyRevitTestResult, self).startTest(test)
        self._started[id(test)] = time.time()
        mlogger.debug("Running test: %s", self.getDescription(test))

    def addSuccess(self, test):
        """Adds a test success.

        Args:
            test (TestCase): unit test case
        """
        super(PyRevitTestResult, self).addSuccess(test)
        mlogger.debug(DEBUG_OKAY_RESULT)
        self.writer.write(RESULT_DIV_OKAY.format(test=self.getDescription(test)))
        self._report("success", test)

    def addError(self, test, err):
        """Adds a test error.

        Args:
            test (TestCase): unit test case
            err (OptExcInfo): test exception info
        """
        super(PyRevitTestResult, self).addError(test, err)
        mlogger.debug(DEBUG_FAIL_RESULT)
        self.writer.write(RESULT_DIV_ERROR.format(test=self.getDescription(test)))
        details = self._exception_detail(test, err)
        self._report("error", test, message=_exception_summary(err), detail=details)
        self._write_exception(details)

    def addFailure(self, test, err):
        """Adds a test failure.

        Args:
            test (TestCase): unit test case
            err (OptExcInfo): test exception info
        """
        super(PyRevitTestResult, self).addFailure(test, err)
        mlogger.debug(DEBUG_FAIL_RESULT)
        self.writer.write(RESULT_DIV_FAIL.format(test=self.getDescription(test)))
        details = self._exception_detail(test, err)
        self._report("failure", test, message=_exception_summary(err), detail=details)
        self._write_exception(details)

    def addSkip(self, test, reason):
        """Adds a skipped test.

        Args:
            test (TestCase): unit test case
            reason (str): why it was skipped
        """
        super(PyRevitTestResult, self).addSkip(test, reason)
        self._report("skipped", test, message=reason)

    def _exception_detail(self, test, err):
        """Renders a failure traceback, falling back to a repr when that fails.

        Args:
            test (TestCase): unit test case
            err (OptExcInfo): test exception info

        Returns:
            (str): traceback text.
        """
        try:
            return self._exc_info_to_string(err, test)
        except Exception:
            return repr(err)

    def _write_exception(self, details):
        """Prints a failure traceback to the output window.

        Args:
            details (str): traceback text.
        """
        mlogger.debug(details)
        self.writer.write("<pre>{}</pre>".format(escape(details)))

    # def addExpectedFailure(self, test, err):
    #     super(PyRevitTestResult, self).addExpectedFailure(test, err)

    # def addUnexpectedSuccess(self, test):
    #     super(PyRevitTestResult, self).addUnexpectedSuccess(test)


class PyRevitTestRunner(object):
    """Test runner.

    Args:
        verbosity (int): level of vermosity. Defaults to 1.
        failfast (bool): if True, stops at the first failure. Defaults to False.
        use_buffer (bool): use a buffer. Defaults to False.
        resultclass (type): Class to use to hold the results.
            Defaults to `PyRevitTestResult`.
        suite_name (str): suite name recorded in the JUnit report.
    """

    resultclass = PyRevitTestResult

    def __init__(
        self,
        verbosity=1,
        failfast=False,
        use_buffer=False,
        resultclass=None,
        suite_name=None,
    ):
        self.verbosity = verbosity
        self.failfast = failfast
        self.use_buffer = use_buffer
        self.suite_name = suite_name
        if resultclass is not None:
            self.resultclass = resultclass

    def _make_result(self):
        return self.resultclass(self.verbosity, suite_name=self.suite_name)

    def run(self, test):
        """Runs a test suite.

        Args:
            test (TestSuite): Test suite to run

        Returns:
            (PyRevitTestResult): Test suite results.
        """
        # setup results object
        result = self._make_result()
        result.failfast = self.failfast
        result.buffer = self.use_buffer

        # start clock
        start_time = time.time()

        # find run test methods
        start_test_run = getattr(result, "startTestRun", None)
        if start_test_run is not None:
            start_test_run()
        try:
            test(result)
        finally:
            stop_test_run = getattr(result, "stopTestRun", None)
            if stop_test_run is not None:
                stop_test_run()

        # stop clock and calculate run time
        stop_time = time.time()
        time_taken = stop_time - start_time

        # print errots
        result.printErrors()
        test_count = result.testsRun
        mlogger.debug(
            "Ran %d test%s in %.3fs",
            test_count,
            test_count != 1 and "s" or "",
            time_taken,
        )

        expected_fails = unexpected_successes = skipped = 0
        try:
            results = map(
                len,
                (result.expectedFailures, result.unexpectedSuccesses, result.skipped),
            )
        except AttributeError:
            pass
        else:
            expected_fails, unexpected_successes, skipped = results

        infos = []
        if not result.wasSuccessful():
            mlogger.debug("FAILED")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            mlogger.debug(DEBUG_OKAY_RESULT)

        if skipped:
            infos.append("skipped=%d" % skipped)
        if expected_fails:
            infos.append("expected failures=%d" % expected_fails)
        if unexpected_successes:
            infos.append("unexpected successes=%d" % unexpected_successes)
        if infos:
            mlogger.debug(" (%s)", (", ".join(infos),))

        return result


def run_module_tests(test_module):
    """Runs the unit tests of the given module.

    Args:
        test_module (module): module with tests

    Returns:
        (PyRevitTestResult): tests results.
    """
    test_runner = PyRevitTestRunner(suite_name=test_module.__name__)
    test_loader = TestLoader()
    # load all testcases from the given module into a testsuite
    test_suite = test_loader.loadTestsFromModule(test_module)
    # run the test suite
    mlogger.debug("Running test suite for module: %s", test_module)
    OutputWriter().write(RESULT_TEST_SUITE_START.format(suite=test_module.__name__))
    return test_runner.run(test_suite)


def run_test_case(test_case):
    """Runs the unit test of the given TestCase class.

    Args:
        test_case (type[TestCase]): TestCase class with tests

    Returns:
        (PyRevitTestResult): tests results.
    """
    suite_name = "{0}.{1}".format(test_case.__module__, test_case.__name__)
    test_runner = PyRevitTestRunner(suite_name=suite_name)
    suite = TestLoader().loadTestsFromTestCase(test_case)
    OutputWriter().write(RESULT_TEST_SUITE_START.format(suite=suite.__class__.__name__))
    return test_runner.run(suite)


def assert_module_tests_successful(test_module):
    """Runs a module's unit tests and fails the command if any of them failed.

    `run_module_tests` only reports; discarding its result makes a red suite
    look like a green button, so command scripts must go through this instead.

    Args:
        test_module (module): module with tests

    Returns:
        (PyRevitTestResult): tests results.

    Raises:
        AssertionError: if the module has failures, errors, or unexpected
            successes. The traceback of each offending test is already in the
            output window, so the message only needs to name the module and the
            counts.

    Note:
        IronPython 2.7's `TestResult.wasSuccessful` ignores
        `unexpectedSuccesses` (`unittest/result.py` returns
        `len(self.failures) == len(self.errors) == 0`), so on the default engine
        an `@expectedFailure` that starts passing does not fail the command.
        CPython does count them, which is why the third count is listed.
    """
    result = run_module_tests(test_module)
    if result.wasSuccessful():
        return result

    counts = [
        "{}={}".format(label, len(issues))
        for label, issues in (
            ("failures", result.failures),
            ("errors", result.errors),
            ("unexpected successes", result.unexpectedSuccesses),
        )
        if issues
    ]
    raise AssertionError(
        "Unit test failures in {}: {}".format(test_module.__name__, ", ".join(counts))
    )
