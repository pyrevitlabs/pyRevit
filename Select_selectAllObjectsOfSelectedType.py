#Select a filled region first and run this.
#this script will select all elements matching the type of the selected filled region
from Autodesk.Revit.DB import FilteredElementCollector
from Autodesk.Revit.UI.Selection import SelElementSet

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

CID = selection[0].Category.Id
TID = selection[0].GetTypeId()

cl = FilteredElementCollector(doc)
list = cl.OfCategoryId(CID).WhereElementIsNotElementType().ToElements()

set = SelElementSet.Create()

for r in list:
	if r.GetTypeId() == TID:
		set.Add(r)
		print("ID: {0}\t{1}\nOWNER VIEW: {2}\n".format(r.Id, r, doc.GetElement(r.OwnerViewId).ViewName ))

uidoc.Selection.Elements = set