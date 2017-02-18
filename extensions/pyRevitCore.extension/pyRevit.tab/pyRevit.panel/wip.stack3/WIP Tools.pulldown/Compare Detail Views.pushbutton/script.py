# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import View

from revitutils import diffutils, selection

view_list = []

for view in selection.elements:
    if isinstance(view, View):
        view_list.append(view)

if len(view_list) == 2:
    print diffutils.compare_views(view_list[0], view_list[1])
