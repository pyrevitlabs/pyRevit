doc = __revit__.ActiveUIDocument.Document
for cat in doc.Settings.Categories:
	print cat.Name