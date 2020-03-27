"""Removes empty tags in current view

Shift+Click:
Remove tags in selected views
"""
#pylint: disable=C0103,E0401
from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms


if __shiftclick__:  #pylint: disable=undefined-variable
    selected_views = \
        forms.select_views(filterfunc=lambda x: isinstance(x, DB.ViewPlan),
                           use_selection=True)
else:
    selected_views = [revit.active_view]

if selected_views:
    itags_ids_to_remove = []
    with revit.Transaction('Removes Empty Tags'):
        # collect
        for view in selected_views:
            vitags = revit.query.get_elements_by_class(
                element_class=DB.IndependentTag,
                doc=revit.doc,
                view_id=view.Id
            )
            for itag in vitags:
                if itag.TagText == "" or itag.TagText is None:
                    itags_ids_to_remove.append(itag.Id)

        # and remove
        revit.doc.Delete(framework.List[DB.ElementId](itags_ids_to_remove))
