# from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

total = 0.0
for i in selection:
	total += i.Parameter['Volume'].AsDouble()
print("TOTAL VOLUME OF ALL SELECTED ELEMENTS IS: {0}".format(total))