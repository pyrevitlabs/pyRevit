from Autodesk.Revit.DB import *
import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

tg = TransactionGroup( doc, "Search for linked elements")
tg.Start()
t = Transaction( doc, "Search for linked elements")
t.Start()

list = []

for el in uidoc.Selection.Elements:
	print("Searching for all objects tied to ELEMENT ID: {0}...".format(el.Id) )
	list = doc.Delete(el.Id)

t.Commit()
tg.RollBack()

for i in list:
	el = doc.GetElement(i)
	if el:
		print("ID: {0}\t\tTYPE: {1}".format(i, el) )
