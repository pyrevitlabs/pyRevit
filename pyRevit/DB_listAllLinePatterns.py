from Autodesk.Revit.DB import FilteredElementCollector, LinePatternElement

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
cl = FilteredElementCollector(doc).OfClass( LinePatternElement )
for i in cl:
	print( i.Name )