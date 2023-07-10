from pyrevit import revit, DB, UI
from pyrevit import forms

import diffutils


view_list = []
selection = revit.get_selection()

for view in selection.elements:
    if isinstance(view, DB.View):
        view_list.append(view)

if len(view_list) == 2:
    res = diffutils.DiffResults()
    comp = diffutils.compare_views(revit.doc,
                                   view_list[0],
                                   view_list[1],
                                   compare_types=__shiftclick__,
                                   diff_results=res)

    forms.alert('Views are smiliar (not identical).'
                if comp else 'Views are NOT smiliar.')

    if not comp:
        revit.uidoc.ActiveView = view_list[0]
        selection.set_to(res.diff_elements)
else:
    forms.alert('Exactly 2 views need to be selected.')
