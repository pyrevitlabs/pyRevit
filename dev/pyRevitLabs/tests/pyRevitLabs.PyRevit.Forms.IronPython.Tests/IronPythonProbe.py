"""Load shared production forms with real IronPython WPF after HostStubs.py."""

import importlib

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
    "dockable",
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
_backend = sys.modules["pyrevit.forms._backend"]
