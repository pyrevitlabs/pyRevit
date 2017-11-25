from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI


__doc__ = 'Uses the Worksharing tooltip to find out the element '\
          '"last edited" by the user in the current view. '\
          'If current view is a sheet, the tools searches all the '\
          'views placed on this sheet as well.' \
          '"Last Edited" elements are elements last edited by the user, '\
          'and are different from borrowed elements.'


filteredlist = []
viewlist = []

selection = revit.get_selection()

if revit.doc.IsWorkshared:
    viewlist.append(revit.activeview.Id)
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
                if wti.LastChangedBy == HOST_APP.username:
                    filteredlist.append(el.Id)
            selection.set_to(filteredlist)
    else:
        pass
else:
    UI.TaskDialog.Show('pyrevit', 'Model is not workshared.')
