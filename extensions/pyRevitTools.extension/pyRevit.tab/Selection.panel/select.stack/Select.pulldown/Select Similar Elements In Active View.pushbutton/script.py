"""Selects elements similar to the currently
selected elements in the active view.

Shift-Click: select in whole project"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit.framework import List

__context__ = 'selection'

if not __shiftclick__:
    # ensure active view is a graphical view
    forms.check_graphicalview(revit.active_view, exitscript=True)

sel_cat_ids = set()

# analyze selection
selection = revit.get_selection()
for el in selection:
    try:
        sel_cat_ids.add(el.Category.Id)
    except Exception:
        continue

if not sel_cat_ids:
    forms.alert("No suitable elements selected", exitscript=True)

mc_filter = DB.ElementMulticategoryFilter(List[DB.ElementId](sel_cat_ids))

# collect from whole model
if __shiftclick__:
    cl = DB.FilteredElementCollector(revit.doc)\
        .WhereElementIsNotElementType()
# collect from a view
else:
    cl = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)\
        .WhereElementIsNotElementType()

match_list = cl.WherePasses(mc_filter).ToElementIds()

selection.set_to(match_list)
revit.uidoc.RefreshActiveView()
