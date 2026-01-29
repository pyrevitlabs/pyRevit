#! python3
"""CPython regression tests.

Validates PR1 contract for pyrevit.forms: import succeeds under CPython and
unsupported symbols raise PyRevitCPythonNotSupported("pyrevit.forms.<symbol>").
"""

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
        """PR1 forms contract: no UI dialogs invoked in stub phase."""
        from pyrevit import PyRevitCPythonNotSupported
        try:
            from pyrevit import forms
        except Exception as err:
            self.fail("pyrevit.forms import failed: {}".format(err))

        try:
            forms.ask_for_string("Test")
            self.fail("Expected PyRevitCPythonNotSupported for ask_for_string")
        except PyRevitCPythonNotSupported as err:
            self.assertEqual(
                "pyrevit.forms.ask_for_string",
                err.feature_name
            )
        except (ImportError, AttributeError) as err:
            self.fail("Unexpected error type for stubbed API: {}".format(err))
        except Exception as err:
            self.fail("Unexpected error type for stubbed API: {}".format(err))

        try:
            getattr(forms, "does_not_exist")
            self.fail("Expected PyRevitCPythonNotSupported for missing symbol")
        except PyRevitCPythonNotSupported as err:
            self.assertEqual(
                "pyrevit.forms.does_not_exist",
                err.feature_name
            )
        except (ImportError, AttributeError) as err:
            self.fail("Unexpected error type for missing symbol: {}".format(err))
        except Exception as err:
            self.fail("Unexpected error type for missing symbol: {}".format(err))

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
