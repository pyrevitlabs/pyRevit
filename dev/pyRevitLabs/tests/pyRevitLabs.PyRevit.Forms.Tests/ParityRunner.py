"""Run every parity test and report each one to the hosting fixture's ``case_log``.

Executed by both the CPython and the IronPython fixture after HostStubs.py and
the engine's forms setup, so each test method becomes its own xUnit row.
Expects ``case_log`` (a managed ``CaseLog``) and ``revit_only_classes`` (a
comma-separated string) in scope. Set the ``PARITY_FILTER`` environment
variable to a substring of ``Class.test_name`` to run only matching tests;
the others then report as not reached.
"""

import os
import unittest

import test_forms_parity

parity_filter = os.environ.get("PARITY_FILTER", "")


class _CaseResult(unittest.TestResult):
    """Forward each test's outcome to the managed log as soon as it is known."""

    def __init__(self, log):
        unittest.TestResult.__init__(self)
        self.log = log

    @staticmethod
    def case_name(test):
        return "{0}.{1}".format(type(test).__name__, test._testMethodName)

    def startTest(self, test):
        unittest.TestResult.startTest(self, test)
        self.log.Start(self.case_name(test))

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test)
        self.log.Pass(self.case_name(test))

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err)
        self.log.Fail(self.case_name(test), self._exc_info_to_string(err, test))

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err)
        self.log.Fail(self.case_name(test), self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason)
        self.log.Skip(self.case_name(test), reason)


parity_suite = unittest.TestSuite()
for parity_name in dir(test_forms_parity):
    parity_class = getattr(test_forms_parity, parity_name)
    if (
        isinstance(parity_class, type)
        and issubclass(parity_class, unittest.TestCase)
        and parity_name not in str(revit_only_classes).split(",")
    ):
        parity_suite.addTests(
            test
            for test in unittest.defaultTestLoader.loadTestsFromTestCase(parity_class)
            if parity_filter in _CaseResult.case_name(test)
        )
parity_suite.run(_CaseResult(case_log))
