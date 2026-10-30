"""Check the Revit API change catalog against the running Revit's API.

Run once per installed Revit version after regenerating the catalog; needs a
pyRevit clone (the catalog lives under dev/, which installers do not ship).
A skipped suite fails this button, since it means nothing was validated.
"""

from pyrevit.unittests import test_revit_api_catalog
from pyrevit.unittests.runner import assert_module_tests_successful

result = assert_module_tests_successful(test_revit_api_catalog)
if result.skipped:
    raise AssertionError(
        "Revit API catalog was not validated: {}".format(
            "; ".join(str(reason) for _, reason in result.skipped)
        )
    )
