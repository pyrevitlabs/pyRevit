"""Activates selection tool that picks a specific type of element."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, catname):
        self.category = catname

    # standard API override function
    def AllowElement(self, element):
        if self.category in element.Category.Name:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):
        return False


def pickbycategory(catname):
    try:
        msfilter = PickByCategorySelectionFilter(catname)
        selection_list = revit.pick_rectangle(pick_filter=msfilter)
        filtered_list = []
        for el in selection_list:
            filtered_list.append(el.Id)
        selection.set_to(filtered_list)
    except Exception:
        pass


options = sorted(['Area',
                  'Area Boundary',
                  'Column',
                  'Dimension',
                  'Door',
                  'Floor',
                  'Framing',
                  'Furniture',
                  'Grid',
                  'Rooms',
                  'Room Tag',
                  'Truss',
                  'Wall',
                  'Window',
                  'Ceiling',
                  'Section Box',
                  'Elevation Mark',
                  'Parking'])

selected_switch = \
    forms.CommandSwitchWindow.show(options,
                                   message='Pick only elements of type:')

if selected_switch:
    pickbycategory(selected_switch)
