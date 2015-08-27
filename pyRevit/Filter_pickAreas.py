__window__.Close()
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


class pickByCategorySelectionFilter(ISelectionFilter):
	def __init__(self, catName):
		self.category = catName
	def AllowElement(self, element):
		if self.category in element.Category.Name:
			return True
		else:
			return False
	def AllowReference(self, refer, point):
		return false

def pickByCategory(catName):
	sel = pickByCategorySelectionFilter( catName )
	list = uidoc.Selection.PickElementsByRectangle(sel)
	set = []
	for el in list:
		set.append( el.Id )
	uidoc.Selection.SetElementIds( List[ElementId]( set ) )

pickByCategory( "Areas" )