"""Load shared production forms with real IronPython WPF and host-only stubs."""

import importlib
import unittest

clr.AddReference(
    "pyRevitLabs.IronPython.Wpf" if sys.version_info[0] == 2 else "IronPython.Wpf"
)
import wpf

framework.wpf = wpf
forms = module("pyrevit.forms", __path__=[os.path.join(fixture_root, "forms")])
host.forms = forms
for name in (
    "base",
    "reactive",
    "dialogs",
    "native",
    "commanddialog",
    "listdialog",
    "promptbars",
    "search",
    "selection",
    "checks",
):
    implementation = importlib.import_module("pyrevit.forms." + name)
    for symbol in dir(implementation):
        if not symbol.startswith("_"):
            setattr(forms, symbol, getattr(implementation, symbol))
host.HOST_APP.proc_screen_workarea = System.Drawing.Rectangle(0, 0, 1920, 1080)
host.HOST_APP.proc_screen_scalefactor = 1.0
sys.modules["pyrevit.revit"].ui.get_window_rectangle = lambda: System.Drawing.Rectangle(
    0, 0, 1920, 1080
)
sys.modules["pyrevit.revit"].ui.get_mainwindow = lambda: None
sys.modules["pyrevit.coreutils"].SafeDict = dict

import test_forms_parity


class RecordingResult(unittest.TextTestResult):
    """Keep the last active case visible when a native modal loop stalls."""

    def startTest(self, test):
        System.Console.WriteLine("Starting " + str(test))
        unittest.TextTestResult.startTest(self, test)

    def stopTest(self, test):
        System.Console.WriteLine("Finished " + str(test))
        unittest.TextTestResult.stopTest(self, test)

    def addError(self, test, error):
        """Expose the Python failure before a later WPF callback can obscure it."""
        System.Console.WriteLine(self._exc_info_to_string(error, test))
        unittest.TextTestResult.addError(self, test, error)


suite = unittest.defaultTestLoader.loadTestsFromModule(test_forms_parity)
report = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(suite)
assert report.wasSuccessful(), str(report.errors) + str(report.failures)
