"""Close selected views"""
from pyrevit import forms
from pyrevit import revit
from pyrevit.compat import get_value_func


uiviews = revit.uidoc.GetOpenUIViews()
views = [revit.doc.GetElement(v.ViewId) for v in uiviews]

views_to_keep = forms.SelectFromList.show(
    [forms.ViewOption(view) for view in views],
    multiselect=True,
    title="Select Views To Keep Open",
    button_name="Keep Selected and Close Others"
    )

if views_to_keep:
    value_func = get_value_func()
    view_ids_to_keep = [value_func(v.Id) for v in views_to_keep]
    uiviews_to_close = filter(
        lambda x: value_func(x.ViewId) not in view_ids_to_keep,
        uiviews)

    for uiview in uiviews_to_close:
        uiview.Close()
