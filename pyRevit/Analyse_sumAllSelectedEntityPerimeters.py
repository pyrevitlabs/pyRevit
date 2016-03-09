uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

total = 0.0
for i in selection:
	total += i.LookupParameter('Perimeter').AsDouble()
print("TOTAL PERIMETER OF ALL SELECTED ELEMENTS IS: {0}".format(total))