"""Activates selection tool that picks a specific type of element.

Shift-Click:
Pick from all available categories.
"""
# pylint: disable=E0401,W0703,C0103
from collections import namedtuple

from pyrevit import revit, UI, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


# somehow DB.BuiltInCategory.OST_Truss does not have a corresponding DB.Category
FREQUENTLY_SELECTED_CATEGORIES = [
    DB.BuiltInCategory.OST_Areas,
    DB.BuiltInCategory.OST_AreaTags,
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


CategoryOption = namedtuple('CategoryOption', ['name', 'revit_cat'])


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, category_opt):
        self.category_opt = category_opt

    # standard API override function
    def AllowElement(self, element):
        if element.Category \
                and self.category_opt.revit_cat.Id == element.Category.Id:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):  # pylint: disable=W0613
        return False


def pick_by_category(category_opt):
    try:
        selection = revit.get_selection()
        msfilter = PickByCategorySelectionFilter(category_opt)
        selection_list = revit.pick_rectangle(pick_filter=msfilter)
        filtered_list = []
        for element in selection_list:
            filtered_list.append(element.Id)
        selection.set_to(filtered_list)
    except Exception as err:
        logger.debug(err)

source_categories = \
    [revit.query.get_category(x) for x in FREQUENTLY_SELECTED_CATEGORIES]
if __shiftclick__:  # pylint: disable=E0602
    source_categories = revit.doc.Settings.Categories

# cleanup source categories
source_categories = filter(None, source_categories)
category_opts = \
    [CategoryOption(name=x.Name, revit_cat=x) for x in source_categories]
selected_category = \
    forms.CommandSwitchWindow.show(
        sorted([x.name for x in category_opts]),
        message='Pick only elements of type:'
    )

if selected_category:
    selected_category_opt = \
        next(x for x in category_opts if x.name == selected_category)
    logger.debug(selected_category_opt)
    pick_by_category(selected_category_opt)
