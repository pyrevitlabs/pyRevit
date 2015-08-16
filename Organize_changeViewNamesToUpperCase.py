from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

t = Transaction(doc, 'Batch Rename Views') 
t.Start()

for el in uidoc.Selection.Elements:
	if isinstance(el, Viewport):
		el = doc.GetElement(el.ViewId)
	name = el.ViewName
	ptos = el.GetParameters('Title on Sheet')[0]
	el.ViewName = el.ViewName.upper()
	ptos.Set(ptos.AsString().upper())
	print("VIEW: {0}\n\tRENAMED TO:\n\t{1}\n\t{2}\n".format(name, el.ViewName, ptos.AsString() ))

t.Commit()