__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, Group, ElementId
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
cl = FilteredElementCollector( doc, curview.Id ).WhereElementIsNotElementType().ToElementIds()

matchlist = []
selCatList = set()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	try:
		selCatList.add( el.Category.Name )
	except:
		continue

for elid in cl:
	el = doc.GetElement( elid )
	try:
		# if el.ViewSpecific and ( el.Category.Name in selCatList):
		if el.Category.Name in selCatList:
			matchlist.append( elid )
	except:
		continue

set = []
for elid in matchlist:
	set.append( elid )

uidoc.Selection.SetElementIds( List[ElementId]( set ) )
uidoc.RefreshActiveView()