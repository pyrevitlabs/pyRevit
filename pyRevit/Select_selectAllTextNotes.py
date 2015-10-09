__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, ElementId, BuiltInCategory, TextNote, Group
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
list = cl.OfClass( TextNote ).WhereElementIsNotElementType().ToElements()

selSet = []

for el in list:
	selSet.append( el.Id )

uidoc.Selection.SetElementIds( List[ElementId]( selSet ) )