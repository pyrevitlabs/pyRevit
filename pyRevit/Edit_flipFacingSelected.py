__window__.Close()
from Autodesk.Revit.DB import Transaction

doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

t = Transaction( doc, 'Flip Facing Selected Doors')
t.Start()

for el in selection:
	if el.Category.Name == 'Doors':
		el.flipFacing()

t.Commit()