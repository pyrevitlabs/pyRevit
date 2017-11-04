"""Removes Underlay From Selected Views."""

# Original Code by dp-stuff.org
# http://dp-stuff.org/revit-view-underlay-property-python-problem/


from pyrevit import HOST_APP
from pyrevit import revit, DB, UI


selection = revit.get_selection()

if selection:
    with revit.Transaction('Batch Set Underlay to None'):
        for element in selection:
            if element.Category.Id.IntegerValue == \
                int(DB.BuiltInCategory.OST_Views) \
                    and (element.CanBePrinted):
                if HOST_APP.is_newer_than(2016):
                    element.SetUnderlayRange(DB.ElementId(-1),
                                             DB.ElementId(-1))
                else:
                    p = element.get_Parameter(
                        DB.BuiltInParameter.VIEW_UNDERLAY_ID
                        )

                    if p is not None:
                        p.Set(DB.ElementId.InvalidElementId)
else:
    UI.TaskDialog.Show('pyRevit', 'Select Views to Remove Underlay')
