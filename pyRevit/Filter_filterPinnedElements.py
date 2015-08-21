uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
from Autodesk.Revit.UI.Selection import SelElementSet

__window__.Close()

pinset = SelElementSet.Create()
for i in uidoc.Selection.Elements:
	if not i.Pinned:
		pinset.Add(i)

uidoc.Selection.Elements = pinset
uidoc.RefreshActiveView()