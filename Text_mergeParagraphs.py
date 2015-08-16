from Autodesk.Revit.DB import Transaction

__window__.Close()
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

t = Transaction(doc, 'Merge Single-Line Text') 
t.Start()

tnotes = sorted( uidoc.Selection.Elements, key = lambda txnote: 0 - txnote.Coord.Y)

mtxt = tnotes[0]
mtxtwidth = mtxt.Width
for txt in tnotes[1:]:
	if txt.Text[0] == '\r\n\r\n':
		mtxt.Text = mtxt.Text + txt.Text
	else:
		mtxt.Text = mtxt.Text + '\r\n\r\n' + txt.Text
	doc.Delete(txt.Id)

mtxt.Width = mtxtwidth
t.Commit()