__window__.Close()
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

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

set = []
for el in list:
	set.append( el.Id )

uidoc.Selection.SetElementIds( List[ElementId]( set ) )
uidoc.RefreshActiveView()