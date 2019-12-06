from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


__doc__ = 'Uses the Worksharing tooltip to find out the element '\
          '"owned" by the user in the current view.' \
          'If current view is a sheet, the tools searches all the '\
          'views placed on this sheet as well.' \
          '"Owned" elements are the elements edited by the user '\
          'since the last synchronize and release.'


filteredlist = []
viewlist = []

selection = revit.get_selection()

if revit.doc.IsWorkshared:
    currentviewid = revit.active_view.Id
    viewlist.append(currentviewid)
    if isinstance(revit.active_view, DB.ViewSheet):
        vportids = revit.active_view.GetAllViewports()
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
            selection.set_to(filteredlist)
    else:
        pass
else:
    forms.alert('Model is not workshared.')
