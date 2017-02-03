"""Updates similar viewports on selected sheets to match the current sheet."""

from Autodesk.Revit.DB import Transaction, Viewport, ViewSheet, ScheduleSheetInstance
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

selSheets = []
selViewports = []

curview = uidoc.ActiveView

for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    if isinstance(el, ViewSheet):
        selSheets.append(el)

if 0 < len(selSheets) <= 2:
    if int(__revit__.Application.VersionNumber) > 2014:
        cursheet = uidoc.ActiveGraphicalView
        for v in selSheets:
            if cursheet.Id == v.Id:
                selSheets.remove(v)
    else:
        cursheet = selSheets[0]
        selSheets.remove(cursheet)

    uidoc.ActiveView = cursheet
    sel = uidoc.Selection.PickObjects(ObjectType.Element)
    for el in sel:
        selViewports.append(doc.GetElement(el))

    if len(selViewports) > 0:
        with Transaction(doc, 'Move Viewports') as t:
            t.Start()
            for sht in selSheets:
                for vp in selViewports:
                    if isinstance(vp, Viewport):
                        viewId = vp.ViewId
                        vpCenter = vp.GetBoxCenter()
                        vpTypeId = vp.GetTypeId()
                        cursheet.DeleteViewport(vp)
                        nvp = Viewport.Create(doc, sht.Id, viewId, vpCenter)
                        nvp.ChangeTypeId(vpTypeId)
                    elif isinstance(vp, ScheduleSheetInstance):
                        nvp = ScheduleSheetInstance.Create(doc, sht.Id, vp.ScheduleId, vp.Point)
                        doc.Delete(vp.Id)

            t.Commit()
    else:
        TaskDialog.Show('pyrevit', 'At least one viewport must be selected.')
elif len(selSheets) == 0:
    TaskDialog.Show('pyrevit', 'You must select at least one sheet to add the selected viewports to.')
elif len(selSheets) > 2:
    TaskDialog.Show('pyrevit', 'Maximum of two sheets can only be selected.')
