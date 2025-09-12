#! python3
"""Regression tests."""

import unittest
from pyrevit.unittests.runner import run_test_case


class TestClass(unittest.TestCase):
    """Unit tests to ensure CPython regressions are not present."""

    def test_enums(self):
        """Issue #2241."""
        from Autodesk.Revit.DB import BuiltInParameter
        element = BuiltInParameter.LEVEL_IS_BUILDING_STORY
        print(type(element))
        self.assertTrue(
            isinstance(element, BuiltInParameter),
            "{} is not a BuiltInParameter".format(type(element))
        )

    def test_pyrevit_forms(self):
        """PyRevit forms compatibility with CPython."""
        try:
            from pyrevit.forms import show_balloon
            show_balloon("It works!", "pyRevit forms is working under CPython")
        except Exception as err:
            print(err)
            self.fail(err)

    def test_ouput_markdown(self):
        """Issue #2130."""
        from pyrevit import script
        output = script.get_output()
        output.print_md('# Hello World!')

    def test_print(self):
        """Issue #2193."""
        import sys
        print(sys.path)

run_test_case(TestClass)
