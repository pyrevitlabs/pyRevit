"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Selects all elements (in model) of the same family as the currently selected object.'

__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, FamilyInstanceFilter, ElementId
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView

matchlist = []

for elId in uidoc.Selection.GetElementIds():
    try:
        el = doc.GetElement(elId)
        family = el.Symbol.Family
        symbolIdSet = family.GetFamilySymbolIds()
        for symid in symbolIdSet:
            cl = FilteredElementCollector(doc).WherePasses(FamilyInstanceFilter(doc, symid)).ToElements()
            for el in cl:
                matchlist.append(el.Id)
    except:
        continue

selSet = []
for elid in matchlist:
    selSet.append(elid)

uidoc.Selection.SetElementIds(List[ElementId](selSet))
uidoc.RefreshActiveView()
