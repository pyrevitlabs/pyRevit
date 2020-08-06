"""Activates selection tool that picks a specific type of element.

Shift-Click:
Pick favorites from all available categories
"""
# pylint: disable=E0401,W0703,C0103
from collections import namedtuple

from pyrevit import revit, UI
from pyrevit import forms
from pyrevit import script

# import this script's configurator
import pick_config


logger = script.get_logger()
my_config = script.get_config()


CategoryOption = namedtuple('CategoryOption', ['name', 'revit_cat'])


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    """Selection filter implementation"""
    def __init__(self, category_opt):
        self.category_opt = category_opt

    def AllowElement(self, element):
        """Is element allowed to be selected?"""
        if element.Category \
                and self.category_opt.revit_cat.Id == element.Category.Id:
            return True
        else:
            return False

    def AllowReference(self, refer, point):  # pylint: disable=W0613
        """Not used for selection"""
        return False


def pick_by_category(category_opt):
    """Handle selection by category"""
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


source_categories = pick_config.load_configs()

# ask user to select a category to select by
if source_categories:
    category_opts = [CategoryOption(name=x.Name, revit_cat=x)
                     for x in source_categories]
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
