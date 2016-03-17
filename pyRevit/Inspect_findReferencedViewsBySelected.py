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

from Autodesk.Revit.DB import View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

el = selection[0]

for i in range(0, el.CurrentViewCount):
	v = doc.GetElement( el.GetViewId(i) )
	print('DETAIL #: {4}\tTYPE: {1}ID: {2}TEMPLATE: {3}  {0}'.format(
			v.ViewName.ljust(100),
			str(v.ViewType).ljust(15),
			str(v.Id).ljust(10),
			str(v.IsTemplate).ljust(10),
			v.LookupParameter('Detail Number').AsString()
		))