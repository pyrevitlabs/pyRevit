"""Print the full path to the central model (if model is workshared)."""

#pylint: disable=E0401
from pyrevit import revit
from pyrevit import forms


forms.check_workshared(doc=revit.doc)
