"""Run the host-handle contract suite in CI without importing the pyrevit package.

The suite lives in ``pyrevit.unittests`` so DevTools can run it on every engine
inside Revit. Importing it through that package pulls in .NET, so it is loaded
here by path; its cases compile production definitions against host doubles.
"""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"


import importlib.util
import unittest
from pathlib import Path


SUITE_PATH = (
    Path(__file__).resolve().parents[4]
    / "pyrevitlib"
    / "pyrevit"
    / "unittests"
    / "test_revit_handle_contract.py"
)


def _load_suite():
    spec = importlib.util.spec_from_file_location(
        "_revit_handle_contract_suite", SUITE_PATH
    )
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    return suite


globals().update(
    {
        name: value
        for name, value in vars(_load_suite()).items()
        if isinstance(value, type) and issubclass(value, unittest.TestCase)
    }
)
