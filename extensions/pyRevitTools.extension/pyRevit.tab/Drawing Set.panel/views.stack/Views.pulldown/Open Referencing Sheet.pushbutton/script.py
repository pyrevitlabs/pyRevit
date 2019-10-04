"""Opens the sheet containing this view and zooms to the viewport."""

from pyrevit import revit, DB


shts = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_Sheets)\
         .WhereElementIsNotElementType()\
         .ToElements()

sheets = sorted(shts, key=lambda x: x.SheetNumber)

curview = revit.active_view
count = 0

for s in sheets:
    vpsIds = [revit.doc.GetElement(x).ViewId for x in s.GetAllViewports()]
    if curview.Id in vpsIds:
        revit.uidoc.ActiveView = s
        vpids = s.GetAllViewports()
        for vpid in vpids:
            vp = revit.doc.GetElement(vpid)
            if curview.Id == vp.ViewId:
                ol = vp.GetBoxOutline()
                revit.uidoc.RefreshActiveView()
                avs = revit.uidoc.GetOpenUIViews()
                for uiv in avs:
                    if uiv.ViewId == s.Id:
                        uiv.ZoomAndCenterRectangle(ol.MinimumPoint,
                                                   ol.MaximumPoint)
