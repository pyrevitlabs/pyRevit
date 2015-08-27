from Autodesk.Revit.DB import FilteredElementCollector, FamilySymbol, Element, ElementType
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector( doc )
list = cl.OfClass( ElementType )

for f in list:
	print( Element.Name.GetValue( f ), ElementType.FamilyName.GetValue( f ))