"""Removes Underlay From Selected Views."""
#pylint: disable=C0103,E0401
# Original Code by dp-stuff.org
# http://dp-stuff.org/revit-view-underlay-property-python-problem/


from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import forms


selected_views = \
    forms.select_views(filterfunc=lambda x: isinstance(x, DB.ViewPlan), use_selection=True)

if selected_views:
    with revit.Transaction('Batch Set Underlay to None'):
        for view in selected_views:
            if view.Category.Id.IntegerValue == \
                    int(DB.BuiltInCategory.OST_Views) \
                    and (view.CanBePrinted):
                if HOST_APP.is_newer_than(2016):
                    view.SetUnderlayRange(DB.ElementId(-1), DB.ElementId(-1))
                else:
                    p = view.get_Parameter(
                        DB.BuiltInParameter.VIEW_UNDERLAY_ID
                        )

                    if p is not None:
                        p.Set(DB.ElementId.InvalidElementId)
