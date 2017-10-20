"""The main pyRevit test is the startup test which is done by launching Revit.

This module is created to provide a platform to perform complete tests on
different components of pyRevit.
For example, as the git module grows, new tests will be added to the git test
suite to test the full functionality of that module, although only a subset of
functions are used during startup and normal operations of pyRevit.
"""

import warnings
warnings.filterwarnings("ignore")

# noinspection PyProtectedMember
from pyrevit.unittests._testrunner import run_module_tests


def perform_engine_tests():
    """Perform Tests on IronPython Engine."""
    # Perform enumtests
    import pyrevit.unittests.ipytests.enumtests as enumtests
    run_module_tests(enumtests)

    # Perform ipycoretests
    import pyrevit.unittests.ipytests.ipycoretests as ipycoretests
    run_module_tests(ipycoretests)


def perform_coreutils_tests():
    """Perform Tests on pyRevit Core Utilities."""
    import pyrevit.unittests.outputtests as outputtests
    run_module_tests(outputtests)
