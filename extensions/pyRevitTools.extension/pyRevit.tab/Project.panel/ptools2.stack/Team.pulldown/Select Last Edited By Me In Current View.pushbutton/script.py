from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


owned_by_me = []
views = []

selection = revit.get_selection()

if revit.doc.IsWorkshared:
    views.append(revit.active_view.Id)
    if isinstance(revit.active_view, DB.ViewSheet):
        vportids = revit.active_view.GetAllViewports()
        for vportid in vportids:
            views.append(revit.doc.GetElement(vportid).ViewId)
    for view in views:
        curviewelements = DB.FilteredElementCollector(revit.doc, view)\
                            .WhereElementIsNotElementType()\
                            .ToElements()

        if len(curviewelements) > 0:
            for el in curviewelements:
                wti = DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                                    el.Id)
                # wti.Creator, wti.Owner, wti.LastChangedBy
                if wti.LastChangedBy == HOST_APP.username:
                    owned_by_me.append(el.Id)
            selection.set_to(owned_by_me)
else:
    forms.alert('Model is not workshared.')
