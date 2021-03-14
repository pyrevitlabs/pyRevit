"""Close selected views"""
from pyrevit import forms
from pyrevit import revit


uiviews = revit.uidoc.GetOpenUIViews()
views = [revit.doc.GetElement(v.ViewId) for v in uiviews]

views_to_keep = forms.SelectFromList.show(
    [forms.ViewOption(view) for view in views],
    multiselect=True,
    title='Select views to keep open'
    )

if views_to_keep:
    view_ids_to_keep = [v.Id.IntegerValue for v in views_to_keep]
    uiviews_to_close = filter(
        lambda x: x.ViewId.IntegerValue not in view_ids_to_keep,
        uiviews)

    for uiview in uiviews_to_close:
        uiview.Close()
