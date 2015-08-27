__window__.Close()
from Autodesk.Revit.DB import Transaction

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

t = Transaction(doc, 'Merge Single-Line Text') 
t.Start()

selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]
tnotes = sorted( selection, key = lambda txnote: 0 - txnote.Coord.Y)

mtxt = tnotes[0]
mtxtwidth = mtxt.Width
for txt in tnotes[1:]:
	if txt.Text[0] == ' ':
		mtxt.Text = mtxt.Text + txt.Text
	else:
		mtxt.Text = mtxt.Text + ' ' + txt.Text
	doc.Delete(txt.Id)

mtxt.Width = mtxtwidth
t.Commit()