__window__.Close()
from Autodesk.Revit.DB import ElementId, Group
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

set = []
for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	if len( list( el.GetMaterialIds(True))) > 0:
		set.append( elId )

uidoc.Selection.SetElementIds( List[ElementId]( set ) )
uidoc.RefreshActiveView()