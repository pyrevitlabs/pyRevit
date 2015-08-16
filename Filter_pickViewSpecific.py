uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

from Autodesk.Revit.DB import Group
from Autodesk.Revit.UI.Selection import ISelectionFilter
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.UI.Selection import SelElementSet

__window__.Close()

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

set = SelElementSet.Create()

for el in list:
	set.Add(el)

# for g in parentGroups:
	# set.Add(g)

uidoc.Selection.Elements = set
uidoc.RefreshActiveView()