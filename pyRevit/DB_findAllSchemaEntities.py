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

__doc__ = 'Lists all elements in the model containing an Extensible Storage Schema entity.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ElementIsElementTypeFilter, LogicalOrFilter
from Autodesk.Revit.DB.ExtensibleStorage import Schema

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

allElements = list(FilteredElementCollector(doc).WherePasses(
    LogicalOrFilter(ElementIsElementTypeFilter(False), ElementIsElementTypeFilter(True))))
guids = {sc.GUID.ToString(): sc.SchemaName for sc in Schema.ListSchemas()}

for el in allElements:
    schemaGUIDs = el.GetEntitySchemaGuids()
    for guid in schemaGUIDs:
        if guid.ToString() in guids.keys():
            print('ELEMENT ID: {0}\t\tSCHEMA NAME: {1}'.format(el.Id.IntegerValue, guids[guid.ToString()]))

print('Iteration completed over {0} elements.'.format(len(allElements)))
