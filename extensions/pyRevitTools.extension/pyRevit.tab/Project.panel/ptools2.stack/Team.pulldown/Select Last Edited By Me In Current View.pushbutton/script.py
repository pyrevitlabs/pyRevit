from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


filteredlist = []
viewlist = []

selection = revit.get_selection()

if revit.doc.IsWorkshared:
    viewlist.append(revit.active_view.Id)
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
                if wti.LastChangedBy == HOST_APP.username:
                    filteredlist.append(el.Id)
            selection.set_to(filteredlist)
    else:
        pass
else:
    forms.alert('Model is not workshared.')
