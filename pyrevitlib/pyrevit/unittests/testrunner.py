import time

from unittest import TestResult

from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


DEBUG_OKAY_RESULT = 'OK'


class PyRevitTestResult(TestResult):
    def __init__(self, verbosity):
        super(PyRevitTestResult, self).__init__(verbosity=verbosity)

    # noinspection PyPep8Naming
    @staticmethod
    def getDescription(test):
        return test.shortDescription()

    # noinspection PyPep8Naming
    def startTest(self, test):
        super(PyRevitTestResult, self).startTest(test)
        logger.debug('Running test: %s' % self.getDescription(test))

    # noinspection PyPep8Naming
    def addSuccess(self, test):
        super(PyRevitTestResult, self).addSuccess(test)
        logger.debug(DEBUG_OKAY_RESULT)

    # def addError(self, test, err):
    #     super(PyRevitTestResult, self).addError(test, err)
    #     if self.showAll:
    #         self.stream.writeln("ERROR")
    #     elif self.dots:
    #         self.stream.write('E')
    #         self.stream.flush()
    #
    # def addFailure(self, test, err):
    #     super(PyRevitTestResult, self).addFailure(test, err)
    #     if self.showAll:
    #         self.stream.writeln("FAIL")
    #     elif self.dots:
    #         self.stream.write('F')
    #         self.stream.flush()
    #
    # def addSkip(self, test, reason):
    #     super(PyRevitTestResult, self).addSkip(test, reason)
    #     if self.showAll:
    #         self.stream.writeln("skipped {0!r}".format(reason))
    #     elif self.dots:
    #         self.stream.write("s")
    #         self.stream.flush()
    #
    # def addExpectedFailure(self, test, err):
    #     super(PyRevitTestResult, self).addExpectedFailure(test, err)
    #     if self.showAll:
    #         self.stream.writeln("expected failure")
    #     elif self.dots:
    #         self.stream.write("x")
    #         self.stream.flush()
    #
    # def addUnexpectedSuccess(self, test):
    #     super(PyRevitTestResult, self).addUnexpectedSuccess(test)
    #     if self.showAll:
    #         self.stream.writeln("unexpected success")
    #     elif self.dots:
    #         self.stream.write("u")
    #         self.stream.flush()
    #
    # def printErrors(self):
    #     if self.dots or self.showAll:
    #         self.stream.writeln()
    #     self.printErrorList('ERROR', self.errors)
    #     self.printErrorList('FAIL', self.failures)
    #
    # def printErrorList(self, flavour, errors):
    #     for test, err in errors:
    #         self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
    #         self.stream.writeln("%s" % err)


class PyRevitTestRunner(object):
    resultclass = PyRevitTestResult

    def __init__(self, descriptions=True, verbosity=1, failfast=False, use_buffer=False, resultclass=None):
        self.descriptions = descriptions
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
        logger.debug("Ran %d test%s in %.3fs" % (test_count, test_count != 1 and "s" or "", time_taken))

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
            logger.debug("FAILED")
            failed, errored = map(len, (result.failures, result.errors))
            if failed:
                infos.append("failures=%d" % failed)
            if errored:
                infos.append("errors=%d" % errored)
        else:
            logger.debug(DEBUG_OKAY_RESULT)

        if skipped:
            infos.append("skipped=%d" % skipped)
        if expected_fails:
            infos.append("expected failures=%d" % expected_fails)
        if unexpected_successes:
            infos.append("unexpected successes=%d" % unexpected_successes)
        if infos:
            logger.debug(" (%s)" % (", ".join(infos),))

        return result
