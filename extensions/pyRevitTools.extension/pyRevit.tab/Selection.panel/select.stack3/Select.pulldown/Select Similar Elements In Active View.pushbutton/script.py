from pyrevit.framework import List
from pyrevit import revit, DB


__context__ = 'selection'
__doc__ = 'Selects elements similar to the currently '\
          'selected elements in the active view .'


cl = DB.FilteredElementCollector(revit.doc, revit.activeview.Id)\
       .WhereElementIsNotElementType()\
       .ToElementIds()

matchlist = []
selCatList = set()

for elId in revit.uidoc.Selection.GetElementIds():
    el = revit.doc.GetElement(elId)
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

revit.uidoc.Selection.SetElementIds(List[DB.ElementId](selSet))
revit.uidoc.RefreshActiveView()
