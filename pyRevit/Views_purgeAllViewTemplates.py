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

__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View, Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()

vtbd = []

for v in views:
	if v.IsTemplate:
		print('ID: {1}		{0}'.format(
				v.ViewName,
				str(v.Id).ljust(10),
			))
		vtbd.append( v )

t = Transaction( doc, 'Remove All View Templates' )
t.Start()

for v in vtbd:
	doc.Delete( v.Id )

t.Commit()