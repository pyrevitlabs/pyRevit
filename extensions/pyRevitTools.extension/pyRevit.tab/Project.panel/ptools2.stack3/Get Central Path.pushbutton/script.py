"""Print the full path to the central model (if model is workshared)."""

#pylint: disable=E0401
from pyrevit import revit
from pyrevit import forms


if forms.check_workshared(doc=revit.doc):
    print(revit.query.get_central_path(doc=revit.doc))