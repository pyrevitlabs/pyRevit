import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Element, Group, GroupType, Transaction, BuiltInParameter, TextNote

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector( doc )
grps = list( cl.OfClass( clr.GetClrType( Group )).ToElements() )

grpTypes = set()

for g in grps:
	mems = g.GetMemberIds()
	for el in mems:
		mem = doc.GetElement( el )
		if isinstance( mem, TextNote):
			grpTypes.add( g.GroupType.Id )

for gtId in grpTypes:
	print( Element.Name.GetValue( doc.GetElement( gtId ) ) )