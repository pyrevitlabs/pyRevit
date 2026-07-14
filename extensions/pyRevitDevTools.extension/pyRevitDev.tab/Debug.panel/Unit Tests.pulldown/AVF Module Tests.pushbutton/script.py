"""Run pyrevit.revit.avf unit tests (requires open project document).

Best run with an AVF-capable active view (e.g. a 3D view); tests that need
AVF are skipped automatically if the active view does not support it.
"""


from pyrevit.unittests import test_avf
from pyrevit.unittests.runner import run_module_tests


run_module_tests(test_avf)
