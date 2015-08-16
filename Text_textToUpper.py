from Autodesk.Revit.DB import Transaction

__window__.Close()
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
 
t = Transaction(doc, 'convert text')
t.Start()

for el in uidoc.Selection.Elements:
	el.Text = el.Text.upper()

t.Commit()