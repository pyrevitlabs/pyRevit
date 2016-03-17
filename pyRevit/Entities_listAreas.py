'''
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
'''

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]


cl = FilteredElementCollector(doc)
list = cl.OfCategory( BuiltInCategory.OST_Areas ).WhereElementIsNotElementType().ToElements()

for el in list:
		print('AREA NAME: {0} AREA NUMBER: {1} AREA ID: {2} LEVEL: {3} AREA: {4}'.format(
			el.LookupParameter('Name').AsString().ljust(30),
			el.LookupParameter('Number').AsString().ljust(10),
			el.Id,
			str(el.Level.Name).ljust(50),
			el.Area,
			))

print('\n\nTOTAL AREAS FOUND: {0}'.format(len(list)))