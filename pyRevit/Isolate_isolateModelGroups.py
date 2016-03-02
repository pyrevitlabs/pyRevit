__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, ElementId, Transaction, Group
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
elements = FilteredElementCollector( doc, curview.Id ).WhereElementIsNotElementType().ToElementIds()

modelgroups = []
expanded = []
for elid in elements:
	el = doc.GetElement( elid )
	if isinstance( el, Group ) and not el.ViewSpecific:
		modelgroups.append( elid )
		members = el.GetMemberIds()
		expanded.extend( list( members ))

expanded.extend( modelgroups )

t = Transaction(doc, 'Isolate Area Boundaries') 
t.Start()

curview.IsolateElementsTemporary( List[ElementId]( expanded ))

t.Commit()