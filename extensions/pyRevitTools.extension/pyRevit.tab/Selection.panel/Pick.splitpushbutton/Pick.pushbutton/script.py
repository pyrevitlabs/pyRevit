"""Activates selection tool that picks a specific type of element."""

from scriptutils.userinput import CommandSwitchWindow
from revitutils import doc, uidoc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Selection import ISelectionFilter
# noinspection PyUnresolvedReferences
from System.Collections.Generic import List


class PickByCategorySelectionFilter(ISelectionFilter):
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
        sel = PickByCategorySelectionFilter(catname)
        sellist = uidoc.Selection.PickElementsByRectangle(sel)
        filteredlist = []
        for el in sellist:
            filteredlist.append(el.Id)
        uidoc.Selection.SetElementIds(List[ElementId](filteredlist))
    except:
        pass


selected_switch = CommandSwitchWindow(sorted(['Area',
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
                                              'Parking', ]), 'Pick only elements of type:').pick_cmd_switch()

if selected_switch is not '':
    pickbycategory(selected_switch)
