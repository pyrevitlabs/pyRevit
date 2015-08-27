__window__.Close()
from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings, LinePatternElement

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

with Transaction(doc, 'Whiteout Selected Elements' ) as t:
	t.Start()
	for el in selection:
		if el.ViewSpecific:
			continue
		elif isinstance( el, Group ):
			for mem in el.GetMemberIds():
				selection.append( doc.GetElement( mem ))
		ogs = OverrideGraphicSettings()
		ogs.SetProjectionLineColor( Color( 255,255,255 ))
		doc.ActiveView.SetElementOverrides( el.Id, ogs );
	t.Commit()