# -*- coding: utf-8 -*-
"""Open the dockable interactive IronPython shell pane.

The pane is registered at pyRevit startup (see pyRevitCore.extension/startup.py) and is visible
by default; this button just ensures it is shown.
"""
from pyrevit import forms

forms.open_dockable_panel("8e2a1f4b-3c57-4d9a-b6e8-7f1a2c3d4e5b")