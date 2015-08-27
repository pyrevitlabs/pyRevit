from Autodesk.Revit.DB import Transaction, TransactionGroup

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = __revit__.ActiveUIDocument.Selection.GetElementIds()

tg = TransactionGroup( doc, "Search for linked elements")
tg.Start()
t = Transaction( doc, "Search for linked elements")
t.Start()

list = []

for elId in selection:
	print("Searching for all objects tied to ELEMENT ID: {0}...".format( elId ))
	list = doc.Delete( elId )

t.Commit()
tg.RollBack()

for elId in list:
	el = doc.GetElement( elId )
	if el and elId in selection:
		print("ID: {0}\t\tTYPE: {1} ( selected object )".format( elId, el.GetType().Name ) )
	elif el:
		print("ID: {0}\t\tTYPE: {1}".format( elId, el.GetType().Name ) )
