from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

deleted = '*deleted'

t = Transaction(doc, 'Categorize views as deleted') 
t.Start()

for el in uidoc.Selection.Elements:
	print("{0} -> {1}".format(el.Parameter['View Type'].AsString(), deleted))
	el.Parameter['View Type'].Set(deleted)
	
t.Commit()