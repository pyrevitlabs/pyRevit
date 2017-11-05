from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI


__doc__ = 'Uses the Worksharing tooltip to find out the element '\
          '"owned" by the user in the current view.' \
          'If current view is a sheet, the tools searches all the '\
          'views placed on this sheet as well.' \
          '"Owned" elements are the elements edited by the user '\
          'since the last synchronize and release.'


filteredlist = []
viewlist = []

if revit.doc.IsWorkshared:
    currentviewid = revit.activeview.Id
    viewlist.append(currentviewid)
    if isinstance(revit.activeview, DB.ViewSheet):
        vportids = revit.activeview.GetAllViewports()
        for vportid in vportids:
            viewlist.append(revit.doc.GetElement(vportid).ViewId)
    for view in viewlist:
        curviewelements = DB.FilteredElementCollector(revit.doc)\
                            .OwnedByView(view)\
                            .WhereElementIsNotElementType()\
                            .ToElements()

        if len(curviewelements) > 0:
            for el in curviewelements:
                wti = DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                                    el.Id)
                # wti.Creator, wti.Owner, wti.LastChangedBy
                if wti.Owner == HOST_APP.username:
                    filteredlist.append(el.Id)
            revit.uidoc.Selection.SetElementIds(
                List[DB.ElementId](filteredlist)
                )
    else:
        pass
else:
    UI.TaskDialog.Show('pyrevit', 'Model is not workshared.')
