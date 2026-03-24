"""Run query.get_name unit tests (requires open project document)."""

__context__ = "doc-project"

from pyrevit.unittests import test_query_get_name
from pyrevit.unittests.runner import run_module_tests


run_module_tests(test_query_get_name)
