from unittest import TestResult

# Make a class that inherits from TestResult (say, MyResults) and implements a bunch of methods.
# Then make a class that inherits from unittest.TextTestRunner (say, MyRunner) and override _makeResult()
# to return an instance of MyResults.
# Then, construct a test suite (which you've probably already got working), and call MyRunner().run(suite).
# You can put whatever behavior you like, including colors, into MyResults.


# class _TestResult(TestResult):
#     def __init__(self, verbosity=1):
#         TestResult.__init__(self)
#
#     def startTest(self, test):
#         TestResult.startTest(self, test)
#

class _TestResult(TestResult):
    def __init__(self, runner):
        TestResult.__init__(self)
        self.runner = runner

    def startTest(self, test):
        TestResult.startTest(self, test)
        self.runner.writeUpdate('<TestCase name=\"%s\" ' % test.shortDescription())

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self.runner.writeUpdate('result="ok" />\n')

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        self.runner.writeUpdate('result="error" />\n')

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        self.runner.writeUpdate('result="fail" />\n')

    def printErrors(self):
        self.printErrorList('Error', self.errors)
        self.printErrorList('Failure', self.failures)

    def printErrorList(self, flavor, errors):
        for test, err in errors:
            self.runner.writeUpdate('<%s testcase="%s">\n' %
                                    (flavor, test.shortDescription()))
            self.runner.writeUpdate('<' + '![CDATA[')
            self.runner.writeUpdate("%s" % err)
            self.runner.writeUpdate(']]' + '>')
            self.runner.writeUpdate("</%s>\n" % flavor)
