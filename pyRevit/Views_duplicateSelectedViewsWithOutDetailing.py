__window__.Close()
from Autodesk.Revit.DB import Transaction, ViewDuplicateOption

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'Duplicate selected views') 
t.Start()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	el.Duplicate( ViewDuplicateOption.Duplicate )
	
t.Commit()