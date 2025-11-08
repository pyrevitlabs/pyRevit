from pyrevit import forms, revit, script, DB
from pyrevit.framework import List

doc = revit.doc
active_view = revit.active_view
uidoc = revit.uidoc

my_config = script.get_config()

exclude_nested = my_config.get_option("exclude_nested", True)
only_current_view = my_config.get_option("only_current_view", True)
reverse_filter = my_config.get_option("reverse_filter", False)

filters = list(revit.query.get_elements_by_class(DB.ParameterFilterElement, doc=doc))

if not filters:
    forms.alert("No Filters found", exitscript=True)

selected_filters = forms.SelectFromList.show(
    sorted(filters, key=lambda f: f.Name),
    name_attr="Name",
    multiselect=True,
    title="Select Filter(s)",
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

view_id = active_view.Id if only_current_view else None

collector = (
    DB.FilteredElementCollector(doc, view_id)
    if view_id
    else DB.FilteredElementCollector(doc)
)

if reverse_filter:
    all_elements = collector.WhereElementIsNotElementType().ToElements()
    filtered_elements = [el for el in all_elements if not combined_filter.PassesFilter(el)]
else:
    filtered_elements = collector.WhereElementIsNotElementType().WherePasses(combined_filter).ToElements()

element_ids = []
for el in filtered_elements:
    if exclude_nested and isinstance(el, DB.FamilyInstance) and el.SuperComponent:
        continue
    element_ids.append(el.Id)

revit.get_selection().set_to(element_ids)
