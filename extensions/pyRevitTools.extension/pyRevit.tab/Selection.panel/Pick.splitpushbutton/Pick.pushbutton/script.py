"""Activates selection tool that picks a specific type of element.

Shift-Click:
Pick from all available categories.
"""

# pylint: disable=E0401,W0703,C0103
from pyrevit import revit, UI, DB
from pyrevit import forms
from pyrevit import script

logger = script.get_logger()


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, catname):
        self.category = catname

    # standard API override function
    def AllowElement(self, element):
        if self.category == element.Category.Name:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):  # pylint: disable=W0613
        return False


def pickbycategory(catname):
    try:
        selection = revit.get_selection()
        msfilter = PickByCategorySelectionFilter(catname)
        selection_list = revit.pick_rectangle(pick_filter=msfilter)
        filtered_list = []
        for element in selection_list:
            filtered_list.append(element.Id)
        selection.set_to(filtered_list)
    except Exception as err:
        logger.debug(err)


if __shiftclick__:  # pylint: disable=E0602
    options = sorted([x.Name for x in revit.doc.Settings.Categories])
else:
    categories_shortlist = [
        DB.BuiltInCategory.OST_Areas,
        DB.BuiltInCategory.OST_AreaSchemeLines,
        DB.BuiltInCategory.OST_Columns,
        DB.BuiltInCategory.OST_StructuralColumns,
        DB.BuiltInCategory.OST_Dimensions,
        DB.BuiltInCategory.OST_Doors,
        DB.BuiltInCategory.OST_Floors,
        DB.BuiltInCategory.OST_StructuralFraming,
        DB.BuiltInCategory.OST_Furniture,
        DB.BuiltInCategory.OST_Grids,
        DB.BuiltInCategory.OST_Rooms,
        DB.BuiltInCategory.OST_RoomTags,
        DB.BuiltInCategory.OST_Truss,
        DB.BuiltInCategory.OST_Walls,
        DB.BuiltInCategory.OST_Windows,
        DB.BuiltInCategory.OST_Ceilings,
        DB.BuiltInCategory.OST_SectionBox,
        DB.BuiltInCategory.OST_ElevationMarks,
        DB.BuiltInCategory.OST_Parking
    ]
    categories_shortlist_ids = [int(x) for x in categories_shortlist]
    categories_filtered = [
        x for x in revit.doc.Settings.Categories if (
            x.Id.IntegerValue in categories_shortlist_ids)]
    options = sorted([x.Name for x in categories_filtered])

selected_switch = \
    forms.CommandSwitchWindow.show(options,
                                   message='Pick only elements of type:')

if selected_switch:
    pickbycategory(selected_switch)
