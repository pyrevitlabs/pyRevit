import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Group, GroupType, Transaction, BuiltInParameter

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list( __revit__.ActiveUIDocument.Selection.Elements )

t = Transaction( doc, 'Explode and Purge Model Groups' )
t.Start()

cl = FilteredElementCollector( doc )
grps = cl.OfClass( clr.GetClrType( Group )).ToElements()

attachedGrps = []

# for g in gt.Groups:
for g in grps:
	if g.Parameter['Attached to']:
		attachedGrps.append( g.GroupType )
	g.UngroupMembers()

for agt in attachedGrps:
	doc.Delete( agt.Id )

cl = FilteredElementCollector( doc )
grpTypes = list( cl.OfClass( clr.GetClrType( GroupType )).ToElements() )

for gt in grpTypes:
	doc.Delete( gt.Id )


t.Commit()

