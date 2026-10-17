"""Check the Revit API change catalog against the running Revit's API.

Run once per installed Revit version after regenerating the catalog; needs a
pyRevit clone (the catalog lives under dev/, which installers do not ship).
"""

from pyrevit.unittests import test_revit_api_catalog
from pyrevit.unittests.runner import assert_module_tests_successful

assert_module_tests_successful(test_revit_api_catalog)
