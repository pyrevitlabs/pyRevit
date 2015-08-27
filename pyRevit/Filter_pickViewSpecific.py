__window__.Close()
from Autodesk.Revit.DB import Group, ElementId
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

parentGroups = set()

class MassSelectionFilter(ISelectionFilter):
	def AllowElement(self, element):
		if element.ViewSpecific:
			if not isinstance(element, Group) and element.GroupId != element.GroupId.InvalidElementId:
				return False
			else:
				return True
		else:
			return False
	def AllowReference(self, refer, point):
		return False

sel = MassSelectionFilter()
list = uidoc.Selection.PickElementsByRectangle(sel)

set = []
for el in list:
	set.append( el.Id )

uidoc.Selection.SetElementIds( List[ElementId]( set ) )
uidoc.RefreshActiveView()