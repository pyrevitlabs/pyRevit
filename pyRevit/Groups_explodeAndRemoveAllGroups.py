__window__.Close()
import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Group, GroupType, Transaction, BuiltInParameter

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction( doc, 'Explode and Purge Model Groups' )
t.Start()

cl = FilteredElementCollector( doc )
grps = list( cl.OfClass( clr.GetClrType( Group )).ToElements() )

cl = FilteredElementCollector( doc )
grpTypes = list( cl.OfClass( clr.GetClrType( GroupType )).ToElements() )

attachedGrps = []

for g in grps:
	if g.LookupParameter('Attached to'):
		attachedGrps.append( g.GroupType )
	g.UngroupMembers()

for agt in attachedGrps:
	doc.Delete( agt.Id )



for gt in grpTypes:
	doc.Delete( gt.Id )

t.Commit()

