"""Run revit module unit tests from pyrevit.unittests."""

from pyrevit.unittests import test_revit_module
from pyrevit.unittests.runner import run_module_tests

run_module_tests(test_revit_module)
