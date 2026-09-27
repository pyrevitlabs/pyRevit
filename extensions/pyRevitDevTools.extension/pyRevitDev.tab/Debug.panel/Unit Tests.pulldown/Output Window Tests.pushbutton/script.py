"""Run output window unit tests from pyrevit.unittests."""

from pyrevit.unittests import test_output_window
from pyrevit.unittests.runner import assert_module_tests_successful

assert_module_tests_successful(test_output_window)
