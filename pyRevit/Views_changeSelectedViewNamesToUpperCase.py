from Autodesk.Revit.DB import Transaction, Viewport

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'Batch Rename Views') 
t.Start()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	if isinstance(el, Viewport):
		el = doc.GetElement(el.ViewId)
	name = el.ViewName
	ptos = el.LookupParameter('Title on Sheet')
	el.ViewName = el.ViewName.upper()
	ptos.Set( ptos.AsString().upper() )
	print("VIEW: {0}\n\tRENAMED TO:\n\t{1}\n\t{2}\n".format( name, el.ViewName, ptos.AsString() ))

t.Commit()