#! python3
"""Register and open the DevTools CPython dockable pane."""

from pyrevit import forms

from cpython_dockable_panel import CPythonDockablePanel
from cpython_dockable_panel import register

register()
forms.open_dockable_panel(CPythonDockablePanel)
