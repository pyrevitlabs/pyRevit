from pyrevit.framework import List
from pyrevit import revit, DB, UI


__context__ = 'selection'
__doc__ = 'Selects all elements (in model) of the same family '\
          'as the currently selected object.'


matchlist = []

for elId in revit.uidoc.Selection.GetElementIds():
    try:
        el = revit.doc.GetElement(elId)
        family = el.Symbol.Family
        symbolIdSet = family.GetFamilySymbolIds()
        for symid in symbolIdSet:
            cl = DB.FilteredElementCollector(revit.doc)\
                   .WherePasses(DB.FamilyInstanceFilter(revit.doc, symid))\
                   .ToElements()
            for el in cl:
                matchlist.append(el.Id)
    except Exception:
        continue

selSet = []
for elid in matchlist:
    selSet.append(elid)

revit.uidoc.Selection.SetElementIds(List[DB.ElementId](selSet))
revit.uidoc.RefreshActiveView()
