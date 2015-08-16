from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

t = Transaction(doc, 'Batch Rename Views') 
t.Start()

for i, el in enumerate(uidoc.Selection.Elements):
	el.Parameter['Detail Number'].Set( str(i+30) )

t.Commit()

__window__.Close()