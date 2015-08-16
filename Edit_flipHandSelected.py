__window__.Close()
from Autodesk.Revit.DB import Transaction

doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

t = Transaction( doc, 'Flip Hand Selected Doors')
t.Start()

for el in selection:
	if el.Category.Name == 'Doors':
		el.flipHand()

t.Commit()