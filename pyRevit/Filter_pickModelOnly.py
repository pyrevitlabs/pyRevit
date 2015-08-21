uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.UI.Selection import SelElementSet

__window__.Close()

class MassSelectionFilter(ISelectionFilter):
	def AllowElement(self, element):
		if not element.ViewSpecific:
			return True
		else:
			return False
	def AllowReference(self, refer, point):
		return false

sel = MassSelectionFilter()

list = uidoc.Selection.PickElementsByRectangle(sel)

set = SelElementSet.Create()

for el in list:
	set.Add(el)

uidoc.Selection.Elements = set
uidoc.RefreshActiveView()