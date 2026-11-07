#! python3
"""Register and open the DevTools CPython dockable pane."""

from pyrevit import forms, script

from cpython_dockable_panel import CPythonDockablePanel
from cpython_dockable_panel import register

if register():
    script.get_logger().warning(
        "startup.cpython.py did not register the CPython dockable pane; "
        "registered it now. Check the pyRevit startup log."
    )
forms.open_dockable_panel(CPythonDockablePanel)
