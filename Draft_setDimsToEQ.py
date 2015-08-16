from Autodesk.Revit.DB import Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__window__.Close()

t = Transaction(doc, 'EQ dimensions')
t.Start()

for el in uidoc.Selection.Elements:
	el.ValueOverride = 'EQ'

t.Commit()