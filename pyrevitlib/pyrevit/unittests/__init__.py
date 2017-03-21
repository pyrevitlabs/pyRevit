"""
The main pyRevit test is the startup test which is done by launching Revit.
This module is created to provide a platform to perform complete tests on different components of pyRevit.
For example, as the git module grows, new tests will be added to the git test suite to test the full functionality
of that module, although only a subset of functions are used during startup and normal operations of pyRevit.
"""
import unittest
import warnings
warnings.filterwarnings("ignore")


test_runner = unittest.TextTestRunner(verbosity=3, buffer=False)
test_loader = unittest.TestLoader()


def _run_module_tests(test_module):
    test_suite = test_loader.loadTestsFromModule(test_module)
    return test_runner.run(test_suite)


def perform_tests():
    # Perform console tests
    import pyrevit.unittests.consoletests
    _run_module_tests(pyrevit.unittests.consoletests)
