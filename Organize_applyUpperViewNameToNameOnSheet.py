from Autodesk.Revit.DB import *
import re
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

t = Transaction(doc, 'Batch Rename Views') 
t.Start()

r = re.compile('\d+\s(.+)')

for el in uidoc.Selection.Elements:
	if isinstance(el, Viewport):
		el = doc.GetElement(el.ViewId)
	name = el.ViewName
	s = r.findall(name)[0].upper()
	ptos = el.GetParameters('Title on Sheet')[0]
	el.ViewName = el.ViewName.upper()
	ptos.Set(s)
	print("VIEW: {0}\n\tTITLE ON SHEET UPDATED TO:\n\t{1}\n".format(name, ptos.AsString() ))

t.Commit()