"""
The main pyRevit test is the startup test which is done by launching Revit.
This module is created to provide a platform to perform complete tests on different components of pyRevit.
For example, as the git module grows, new tests will be added to the git test suite to test the full functionality
of that module, although only a subset of functions are used during startup and normal operations of pyRevit.
"""

import warnings
warnings.filterwarnings("ignore")

from unittest import TestLoader

from pyrevit.coreutils.logger import get_logger
from pyrevit.unittests.testrunner import PyRevitTestRunner


logger = get_logger(__name__)


test_runner = PyRevitTestRunner()
test_loader = TestLoader()


def _run_module_tests(test_module):
    # load all testcases from the given module into a testsuite
    test_suite = test_loader.loadTestsFromModule(test_module)
    # run the test suite
    logger.debug('Running test suite for module: %s' % test_module)
    return test_runner.run(test_suite)


def perform_tests():
    # Perform revitutilstests
    import pyrevit.unittests.revitutilstests
    _run_module_tests(pyrevit.unittests.revitutilstests)

    # Perform consoletests
    import pyrevit.unittests.consoletests
    _run_module_tests(pyrevit.unittests.consoletests)
