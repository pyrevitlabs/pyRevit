__window__.Close()
from Autodesk.Revit.DB import Transaction

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
 
t = Transaction(doc, 'convert text')
t.Start()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	el.Text = el.Text.upper()

t.Commit()