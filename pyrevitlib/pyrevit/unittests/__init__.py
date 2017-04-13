"""
The main pyRevit test is the startup test which is done by launching Revit.
This module is created to provide a platform to perform complete tests on different components of pyRevit.
For example, as the git module grows, new tests will be added to the git test suite to test the full functionality
of that module, although only a subset of functions are used during startup and normal operations of pyRevit.
"""

import warnings
warnings.filterwarnings("ignore")

from pyrevit.coreutils.logger import get_logger
from pyrevit.unittests.testrunner import run_module_tests


logger = get_logger(__name__)


def perform_tests():
    # Perform enumtests
    # import pyrevit.unittests.enumtests as enumtests
    # run_module_tests(enumtests)
    
    # Perform ipycoretests
    import pyrevit.unittests.ipycoretests as ipycoretests
    run_module_tests(ipycoretests)

    # Perform revitutilstests
    import pyrevit.unittests.revitutilstests as revitutilstests
    run_module_tests(revitutilstests)

    # Perform consoletests
    import pyrevit.unittests.consoletests as consoletests
    run_module_tests(consoletests)
