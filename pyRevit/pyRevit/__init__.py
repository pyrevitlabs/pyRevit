uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit.UI.Selection import SelElementSet

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
	set = SelElementSet.Create()
	for el in list:
		set.Add(el)
	uidoc.Selection.Elements = set