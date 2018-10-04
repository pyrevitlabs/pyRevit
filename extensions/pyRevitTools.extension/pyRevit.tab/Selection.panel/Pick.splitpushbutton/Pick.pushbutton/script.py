"""Activates selection tool that picks a specific type of element.

Shift-Click:
Pick from all available categories.
"""

#pylint: disable=E0401,W0703,C0103
from pyrevit import revit, UI
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


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
    def AllowReference(self, refer, point): #pylint: disable=W0613
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



if __shiftclick__:  #pylint: disable=E0602
    options = sorted([x.Name for x in revit.doc.Settings.Categories])
else:
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
