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

module("pyrevit._perf", mark=lambda label: None)
module(
    "Autodesk",
    __path__=[],
    Windows=module(
        "Autodesk.Windows",
        __path__=[],
        ComponentManager=module("Autodesk.Windows.ComponentManager"),
    ),
    Internal=module(
        "Autodesk.Internal",
        __path__=[],
        InfoCenter=module("Autodesk.Internal.InfoCenter"),
    ),
)
facade = importlib.import_module("pyrevit.forms._ipy_legacy")
unresolved = [name for name in facade.__all__ if not hasattr(facade, name)]
assert not unresolved, unresolved
assert len(set(facade.__all__)) == len(facade.__all__)
dockable = sys.modules["pyrevit.forms.dockable"]
assert facade.WPFPanel is dockable.WPFPanel
assert facade.toggle_dockable_panel is dockable.toggle_dockable_panel


class IronPythonProbePanel(facade.WPFPanel):
    """Load an IronPython dockable page through the shared panel module."""

    panel_id = "6d1f3c3e-5a40-4a8e-9a43-2f1b9d0c7e11"
    panel_source = os.path.join(fixture_root, "PanelProbe.xaml")
    panel_title = "IronPython Panel Probe"


registered_panel = facade.register_dockable_panel(
    IronPythonProbePanel, default_visible=False
)
assert isinstance(registered_panel, Controls.Page)
assert registered_panel.label.Text == "Panel probe"
assert facade.is_registered_dockable_panel(IronPythonProbePanel)
provider = _DockablePane.registered[IronPythonProbePanel.panel_id][1]
pane_data = types.SimpleNamespace()
provider.SetupDockablePane(pane_data)
assert pane_data.FrameworkElement is registered_panel
assert pane_data.VisibleByDefault is False
pane = facade.get_dockable_panel(IronPythonProbePanel)
uiapp = host.HOST_APP.uiapp
facade.open_dockable_panel(IronPythonProbePanel)
facade.open_dockable_panel(IronPythonProbePanel)
assert not pane.is_visible
assert len(uiapp.Idling.handlers) == 1
facade.close_dockable_panel(IronPythonProbePanel)
uiapp.raise_idling()
assert not uiapp.Idling.handlers
assert facade.is_registered_dockable_panel(registered_panel)
facade.open_dockable_panel(IronPythonProbePanel)
_DockablePane.created.update(_DockablePane.registered)
uiapp.raise_idling()
assert pane.is_visible
assert not uiapp.Idling.handlers
facade.close_dockable_panel(IronPythonProbePanel.panel_id)
assert not pane.is_visible
