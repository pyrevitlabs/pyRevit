# -*- coding: utf-8 -*-
"""AVF example — remove the values this example shows in the active view."""

from pyrevit import forms
from pyrevit import revit
from pyrevit.revit import avf

RESULT_NAME = "pyRevitAVF_Demo"

removed = avf.clear_values(revit.active_view, RESULT_NAME)
forms.alert("Removed {} value(s) from the active view.".format(removed))
