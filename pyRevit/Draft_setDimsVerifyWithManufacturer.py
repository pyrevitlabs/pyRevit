__window__.Close()
from Autodesk.Revit.DB import Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'VWM dimensions')
t.Start()

for elId in uidoc.Selection.GetElementIds():
	el = doc.GetElement( elId )
	el.Suffix = 'R.O.'
	el.Below = 'VERIFY W/ MFR'

t.Commit()