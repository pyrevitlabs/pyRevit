from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

t = Transaction(doc, 'Duplicate selected views') 
t.Start()

for el in uidoc.Selection.Elements:
	el.Duplicate(ViewDuplicateOption.WithDetailing)
	
t.Commit()