__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory, ElementId, Wall
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

set = []
curview = uidoc.ActiveGraphicalView
elements = FilteredElementCollector( doc, curview.Id ).WhereElementIsNotElementType().ToElementIds()
for elId in elements:
	el = doc.GetElement( elId )
	if len( list( el.GetMaterialIds(True))) > 0:
		set.append( elId )
	elif isinstance(el, Wall) and el.IsStackedWall:
		memberWalls = el.GetStackedWallMemberIds()
		for mwid in memberWalls:
			mw = doc.GetElement( mwid )
			if len( list( mw.GetMaterialIds(True))) > 0:
				set.append( elId )

t = Transaction(doc, 'Isolate painted Elements') 
t.Start()

curview.IsolateElementsTemporary( List[ElementId]( set ) )

t.Commit()