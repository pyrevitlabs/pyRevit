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

__doc__ = ''

__window__.Close()

import clr
from Autodesk.Revit.DB import Category, Transaction, BuiltInCategory
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

bicat = BuiltInCategory.OST_Ceilings

def convertToCat( family, bicat ):
	famdoc = doc.EditFamily( family )
	catobj = Category.GetCategory( famdoc, bicat )
	famdoc.OwnerFamily.FamilyCategory = catobj
	famdoc.LoadFamily( doc )

def convertToCat( bicat ):
	with Transaction( doc, 'Convert Family' ) as t:
			t.Start()
			catobj = Category.GetCategory( doc, bicat )
			doc.OwnerFamily.FamilyCategory = catobj
			doc.Regenerate()
			t.Commit()

if len( selection ) > 0 and not doc.IsFamilyDocument:
	for el in selection:
		convertToCat( el.Symbol.Family, bicat )
else:
	convertToCat( bicat )