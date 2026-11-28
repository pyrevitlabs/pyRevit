# -*- coding: utf-8 -*-
"""tmpgfx example — remove the icons this example placed."""

from pyrevit.revit import tmpgfx

TOOL_NAME = "pyRevitDev.TemporaryGraphicsExample"

tmpgfx.dispose(TOOL_NAME)
