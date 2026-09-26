"""Run script module unit tests from pyrevit.unittests."""

from pyrevit.unittests import test_script_module
from pyrevit.unittests.runner import assert_module_tests_successful

assert_module_tests_successful(test_script_module)
