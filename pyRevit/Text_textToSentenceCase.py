__window__.Close()
from Autodesk.Revit.DB import Transaction

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
 
t = Transaction(doc, 'to Sentence case')
t.Start()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	el.Text = str(el.Text)[0].upper() + str(el.Text[1:]).lower()

t.Commit()