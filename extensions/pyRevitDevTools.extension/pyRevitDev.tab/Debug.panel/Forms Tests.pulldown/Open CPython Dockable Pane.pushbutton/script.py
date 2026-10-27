#! python3
"""Register and open the DevTools CPython dockable pane."""

from pyrevit import forms, script


class CPythonDockablePanel(forms.WPFPanel):
    """Provide a minimal interactive CPython dockable-pane fixture."""

    panel_id = "99831b89-2a75-499f-a86a-ea45723cc560"
    panel_source = script.get_bundle_file("ui.xaml")
    panel_title = "pyRevit CPython Dockable Panel"

    def increment(self, sender, args):
        """Update the visible interaction counter."""
        self.count += 1
        self.status.Text = "Clicked {} time(s)".format(self.count)

    def __init__(self):
        forms.WPFPanel.__init__(self)
        self.count = 0


if not forms.is_registered_dockable_panel(CPythonDockablePanel):
    forms.register_dockable_panel(CPythonDockablePanel)

forms.open_dockable_panel(CPythonDockablePanel)
