__window__.Close()
from Autodesk.Revit.DB import Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

t = Transaction(doc, 'Shift Viewports by 30') 
t.Start()

for i, el in enumerate( selection ):
	el.LookupParameter('Detail Number').Set( str(i+30) )

t.Commit()

