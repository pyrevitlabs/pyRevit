"""Close selected views."""
from pyrevit import forms, revit

doc = revit.doc
uidoc = revit.uidoc

uiviews = uidoc.GetOpenUIViews()
views = [doc.GetElement(uiview.ViewId) for uiview in uiviews]

list_items = [forms.ViewOption(view) for view in views]

views_to_keep = forms.SelectFromList.show(list_items,
                                          multiselect=True,
                                          title='Select views to keep open')

if not views_to_keep:
    script.exit()

uiviews_to_close = filter(
    lambda x: x.ViewId.IntegerValue not in \
    [view.Id.IntegerValue for view in views_to_keep],
    uiviews)

for uiview in uiviews_to_close:
    uiview.Close()
