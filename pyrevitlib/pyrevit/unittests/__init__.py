"""
The main pyRevit test is the startup test which is done by launching Revit.
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
    # Perform enumtests
    import pyrevit.unittests.ipytests.enumtests as enumtests
    run_module_tests(enumtests)

    # Perform ipycoretests
    import pyrevit.unittests.ipytests.ipycoretests as ipycoretests
    run_module_tests(ipycoretests)


def perform_coreutils_tests():
    import pyrevit.unittests.consoletests as consoletests
    run_module_tests(consoletests)


def perform_scriptutilstests():
    import pyrevit.unittests.scriptutilstests as scriptutilstests
    run_module_tests(scriptutilstests)


def perform_revitutils_tests():
    import pyrevit.unittests.revitutilstests as revitutilstests
    run_module_tests(revitutilstests)
