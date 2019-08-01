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