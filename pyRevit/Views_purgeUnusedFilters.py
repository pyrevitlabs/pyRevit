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

__doc__ = 'Deletes all view parameter filters that has not been listed on any views. This includes sheets as well.'

__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View, ParameterFilterElement, Transaction, \
    ElementId

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

views = FilteredElementCollector(doc).OfClass(View).WhereElementIsNotElementType().ToElements()
filters = FilteredElementCollector(doc).OfClass(ParameterFilterElement).ToElements()

usedFiltersSet = set()
allFilters = set()
for flt in filters:
    allFilters.add(flt.Id.IntegerValue)

for v in views:
    try:
        filters = v.GetFilters()
        for flid in filters:
            usedFiltersSet.add(flid.IntegerValue)
    except:
        continue

unusedFilters = allFilters - usedFiltersSet

t = Transaction(doc, 'Purge Unused Filters')
t.Start()

for flid in unusedFilters:
    fl = doc.GetElement(ElementId(flid))
    print('ID: {0}\t{1}'.format(fl.Id, fl.Name))
    doc.Delete(ElementId(flid))

t.Commit()
