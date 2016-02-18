__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, FamilyInstanceFilter, ElementId
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView

matchlist = []
famSymbolList = set()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	famSymbolList.add( doc.GetElement( el.GetTypeId()))

for fsym in famSymbolList:
	try:
		family = fsym.Family
	except:
		continue
	symbolSet = family.Symbols
	for sym in symbolSet:
		cl = FilteredElementCollector(doc).WherePasses( FamilyInstanceFilter( doc, sym.Id )).ToElements()
		for el in cl:
			matchlist.append( el.Id )

set = []
for elid in matchlist:
	set.append( elid )

uidoc.Selection.SetElementIds( List[ElementId]( set ) )
uidoc.RefreshActiveView()