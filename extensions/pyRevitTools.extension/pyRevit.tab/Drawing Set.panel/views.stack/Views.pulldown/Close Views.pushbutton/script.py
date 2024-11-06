"""Close selected views"""
from pyrevit import forms
from pyrevit import revit
from pyrevit.compat import get_elementid_value_func


uiviews = revit.uidoc.GetOpenUIViews()
views = [revit.doc.GetElement(v.ViewId) for v in uiviews]

views_to_keep = forms.SelectFromList.show(
    [forms.ViewOption(view) for view in views],
    multiselect=True,
    title="Select Views To Keep Open",
    button_name="Keep Selected and Close Others"
    )

if views_to_keep:
    get_elementid_value = get_elementid_value_func()
    view_ids_to_keep = [get_elementid_value(v.Id) for v in views_to_keep]
    uiviews_to_close = filter(
        lambda x: get_elementid_value(x.ViewId) not in view_ids_to_keep,
        uiviews)

    for uiview in uiviews_to_close:
        uiview.Close()
