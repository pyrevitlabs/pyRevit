"""Shared CPython dockable panel registration for DevTools."""

import os

from pyrevit import forms


class CPythonDockablePanel(forms.WPFPanel):
    """Provide an interactive CPython dockable-pane fixture."""

    panel_id = "99831b89-2a75-499f-a86a-ea45723cc560"
    panel_source = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "CPythonDockablePanel.xaml",
    )
    panel_title = "pyRevit CPython Dockable Panel"

    def __init__(self):
        forms.WPFPanel.__init__(self)
        self.count = 0

    def increment(self, sender, args):
        """Update the visible interaction counter."""
        self.count += 1
        self.status.Text = "Clicked {} time(s)".format(self.count)


def register():
    """Register the panel with Revit unless it is already registered.

    ``startup.cpython.py`` calls this during startup. The Open CPython Dockable
    Pane button calls it again as a fallback and reports when it had to.

    Returns:
        bool: True when this call registered the panel.
    """
    if forms.is_registered_dockable_panel(CPythonDockablePanel):
        return False
    forms.register_dockable_panel(CPythonDockablePanel, default_visible=False)
    return True
