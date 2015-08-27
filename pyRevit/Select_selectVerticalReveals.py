__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, ElementId, BuiltInCategory
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
list = cl.OfCategory( BuiltInCategory.OST_Reveals ).WhereElementIsNotElementType().ToElements()

selSet = []

for el in list:
	if el.GetWallSweepInfo().IsVertical:
		selSet.append( el.Id )

uidoc.Selection.SetElementIds( List[ElementId]( selSet ) )