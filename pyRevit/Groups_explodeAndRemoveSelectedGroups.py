__window__.Close()
import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Group, GroupType, Transaction, BuiltInParameter
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

t = Transaction( doc, 'Explode and Purge Selected Groups' )
t.Start()

grpTypes = set()
grps = []
attachedGrps = []

for el in selection:
	if isinstance(el, GroupType):
		grpTypes.add( el )
	elif isinstance(el, Group):
		grpTypes.add( el.GroupType )

if len(grpTypes) == 0:
	TaskDialog.Show('pyRevit', 'At least one group type must be selected.')


for gt in grpTypes:
	for grp in gt.Groups:
		grps.append( grp )

for g in grps:
	if g.LookupParameter('Attached to'):
		attachedGrps.append( g.GroupType )
	g.UngroupMembers()

for agt in attachedGrps:
	doc.Delete( agt.Id )

for gt in grpTypes:
	doc.Delete( gt.Id )

t.Commit()

