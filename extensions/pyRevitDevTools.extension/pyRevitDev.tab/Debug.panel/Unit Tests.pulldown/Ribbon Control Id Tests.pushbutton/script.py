"""Run ribbon control id tests from pyrevit.unittests."""

from pyrevit.unittests import test_ribbon_control_ids
from pyrevit.unittests.runner import assert_module_tests_successful

assert_module_tests_successful(test_ribbon_control_ids)
