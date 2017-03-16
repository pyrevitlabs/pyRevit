"""
The main pyRevit test is the startup test which is done by launching Revit.
This module is created to provide a platform to perform complete tests on different components of pyRevit.
For example, as the git module grows, new tests will be added to the git test suite to test the full functionality
of that module, although only a subset of functions are used during startup and normal operations of pyRevit.
"""


import unittest
import pyrevit.unittests.consoletests


def perform_tests():
    testsuite = unittest.TestLoader().loadTestsFromModule(pyrevit.unittests.consoletests)
    test_result = unittest.TextTestRunner(verbosity=3, buffer=False).run(testsuite)
