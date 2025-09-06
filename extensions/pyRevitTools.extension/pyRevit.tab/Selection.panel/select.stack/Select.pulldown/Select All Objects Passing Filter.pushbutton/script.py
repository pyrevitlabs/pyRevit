from pyrevit import forms, revit, script, DB
from pyrevit.framework import List

doc = revit.doc
active_view = revit.active_view
uidoc = revit.uidoc

filters = list(DB.FilteredElementCollector(doc).OfClass(DB.ParameterFilterElement))

if not filters:
    forms.alert("No Filters found", exitscript=True)

selected_filters = forms.SelectFromList.show(
    sorted(filters, key=lambda f: f.Name),
    name_attr='Name',
    multiselect=True,
    title='Select Filter(s)'
)

if not selected_filters:
    script.exit()

element_filters = []
for f in selected_filters:
    ef = f.GetElementFilter()
    if ef:
        element_filters.append(ef)

if not element_filters:
    forms.alert("No valid ElementFilters found.", exitscript=True)

combined_filter = DB.LogicalOrFilter(List[DB.ElementFilter](element_filters))

collector = DB.FilteredElementCollector(doc, active_view.Id)
filtered_elements = collector.WherePasses(combined_filter).ToElements()

if not filtered_elements:
    forms.alert("No Elements pass that Filter", exitscript=True)

element_ids = [el.Id for el in filtered_elements]
uidoc.Selection.SetElementIds(List[DB.ElementId](element_ids))
