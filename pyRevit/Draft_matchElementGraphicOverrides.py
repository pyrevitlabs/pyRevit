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
__doc__ = 'pick the source object that has the element GRAPHICS OVERRIDE you like to match to, and then pick the destination objects one by one and this toll will match the graphics.'

from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory, ElementId
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
curview = doc.ActiveView

verbose = True

__window__.Close()

sel = []
sourceElement = doc.GetElement( uidoc.Selection.PickObject(ObjectType.Element, 'Pick source object.') )
fromStyle = curview.GetElementOverrides( sourceElement.Id )

while True:
	try:
		destElement = doc.GetElement( uidoc.Selection.PickObject(ObjectType.Element, 'Pick objects to change their graphic overrides.') )
		with Transaction(doc, 'Match Graphics Overrides') as t:
			t.Start()
			curview.SetElementOverrides( destElement.Id, fromStyle)
			t.Commit()
	except:
		break
