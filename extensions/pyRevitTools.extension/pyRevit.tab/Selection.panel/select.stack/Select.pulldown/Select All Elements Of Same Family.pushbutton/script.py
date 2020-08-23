from pyrevit.framework import List
from pyrevit import revit, DB, UI


matchlist = []
families_checked = []

selection = revit.get_selection()

for el in selection:
    try:
        # allow to select Type (FamilySymbol) from ProjectBrowser
        if isinstance(el, DB.FamilySymbol):
            symbol = el
        else:
            symbol = el.Symbol
        family = symbol.Family
        # do not collect element of the same family twice
        if family.Id in families_checked:
            continue
        families_checked.append(family.Id)
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

selection.set_to(selSet)
revit.uidoc.RefreshActiveView()
