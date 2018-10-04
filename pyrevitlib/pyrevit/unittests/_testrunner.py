import time
from unittest import TestResult, TestLoader

from pyrevit.coreutils.logger import get_logger
from pyrevit.output import get_output


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


DEBUG_OKAY_RESULT = 'PASSED'
DEBUG_FAIL_RESULT = 'FAILED'

RESULT_TEST_SUITE_START = '<div class="unittest unitteststart">' \
                          'Test Suite: {suite}' \
                          '</div>'

RESULT_DIV_OKAY = '<div class="unittest unittestokay">' \
                  ':white_heavy_check_mark: PASSED {test}' \
                  '</div>'

RESULT_DIV_FAIL = '<div class="unittest unittestfail">' \
                  ':cross_mark: FAILED {test}' \
                  '</div>'

RESULT_DIV_ERROR = '<div class="unittest unittesterror">' \
                   ':heavy_large_circle: ERROR {test}' \
                   '</div>'


class OutputWriter:
    def __init__(self):
        self._output = get_output()

    def write(self, output_str):
        self._output.print_html(output_str)


class PyRevitTestResult(TestResult):
    def __init__(self, verbosity):
        super(PyRevitTestResult, self).__init__(verbosity=verbosity)
        self.writer = OutputWriter()

    @staticmethod
    def getDescription(test):
        return test.shortDescription() if test.shortDescription() else test

    def startTest(self, test):
        super(PyRevitTestResult, self).startTest(test)
        mlogger.debug('Running test: %s', self.getDescription(test))

    def addSuccess(self, test):
        super(PyRevitTestResult, self).addSuccess(test)
        mlogger.debug(DEBUG_OKAY_RESULT)
        self.writer.write(RESULT_DIV_OKAY
                          .format(test=self.getDescription(test)))

    def addError(self, test, err):
        super(PyRevitTestResult, self).addError(test, err)
        mlogger.debug(DEBUG_FAIL_RESULT)
        self.writer.write(RESULT_DIV_ERROR
                          .format(test=self.getDescription(test)))

    def addFailure(self, test, err):
        super(PyRevitTestResult, self).addFailure(test, err)
        mlogger.debug(DEBUG_FAIL_RESULT)
        self.writer.write(RESULT_DIV_FAIL
                          .format(test=self.getDescription(test)))

    # def addSkip(self, test, reason):
    #     super(PyRevitTestResult, self).addSkip(test, reason)

    # def addExpectedFailure(self, test, err):
    #     super(PyRevitTestResult, self).addExpectedFailure(test, err)

    # def addUnexpectedSuccess(self, test):
    #     super(PyRevitTestResult, self).addUnexpectedSuccess(test)


class PyRevitTestRunner(object):
    resultclass = PyRevitTestResult

    def __init__(self, verbosity=1, failfast=False,
                 use_buffer=False, resultclass=None):
        self.verbosity = verbosity
        self.failfast = failfast
        self.use_buffer = use_buffer
        if resultclass is not None:
            self.resultclass = resultclass

    def _make_result(self):
        return self.resultclass(self.verbosity)

    def run(self, test):
        # setup results object
        result = self._make_result()
        result.failfast = self.failfast
        result.buffer = self.use_buffer

        # start clock
        start_time = time.time()

        # find run test methods
        start_test_run = getattr(result, 'startTestRun', None)
        if start_test_run is not None:
            start_test_run()
        try:
            test(result)
        finally:
            stop_test_run = getattr(result, 'stopTestRun', None)
            if stop_test_run is not None:
                stop_test_run()

        # stop clock and calculate run time
        stop_time = time.time()
        time_taken = stop_time - start_time

        # print errots
        result.printErrors()
        test_count = result.testsRun
        mlogger.debug("Ran %d test%s in %.3fs",
                      test_count, test_count != 1 and "s" or "", time_taken)

        expected_fails = unexpected_successes = skipped = 0
        try:
            results = map(len, (result.expectedFailures,
                                result.unexpectedSuccesses,
                                result.skipped))
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
    test_runner = PyRevitTestRunner()
    test_loader = TestLoader()
    # load all testcases from the given module into a testsuite
    test_suite = test_loader.loadTestsFromModule(test_module)
    # run the test suite
    mlogger.debug('Running test suite for module: %s', test_module)
    OutputWriter()\
        .write(RESULT_TEST_SUITE_START.format(suite=test_module.__name__))
    return test_runner.run(test_suite)
