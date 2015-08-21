import Autodesk.Revit.DB
import Autodesk.Revit.UI
from Autodesk.Revit.UI.Selection import SelElementSet

cl = FilteredElementCollector(doc)
list = cl.OfCategory(BuiltInCategory.OST_Reveals).WhereElementIsNotElementType().ToElements()

selSet = SelElementSet.Create()

for el in list:
	if el.GetWallSweepInfo().IsVertical:
		selSet.Add(el)

uidoc.Selection.Elements = selSet