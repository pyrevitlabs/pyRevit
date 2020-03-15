"""Selects elements similar to the currently
selected elements in the active view."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, DB
from pyrevit import forms


__context__ = 'selection'


# ensure active view is a graphical view
forms.check_graphicalview(revit.active_view, exit_script=True)

cl = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)\
       .WhereElementIsNotElementType()\
       .ToElementIds()

matchlist = []
selCatList = set()

selection = revit.get_selection()

for el in selection:
    try:
        selCatList.add(el.Category.Name)
    except Exception:
        continue

for elid in cl:
    el = revit.doc.GetElement(elid)
    try:
        # if el.ViewSpecific and ( el.Category.Name in selCatList):
        if el.Category.Name in selCatList:
            matchlist.append(elid)
    except Exception:
        continue

selSet = []
for elid in matchlist:
    selSet.append(elid)

selection.set_to(selSet)
revit.uidoc.RefreshActiveView()
