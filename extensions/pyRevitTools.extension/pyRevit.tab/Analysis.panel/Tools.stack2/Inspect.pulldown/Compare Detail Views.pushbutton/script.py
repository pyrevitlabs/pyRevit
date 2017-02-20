from revitutils import uidoc, diffutils, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import View
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


__doc__ = 'Compared two views by comparing the contents against each other. by default, This tool does not '      \
          'pay attention to the element types. For example, two text elements having the same contents '          \
          'but with different styles are considered equal. This however can be overriden using the SHIFT-Click. ' \
          'If the views do not match, all the different elements will be selected. '                              \
          'This tool is helpful when comparing duplicate detail views.'                                           \
          '\n\nSHIFT-Click: Include Element Types in Comparison'


view_list = []

for view in selection.elements:
    if isinstance(view, View):
        view_list.append(view)

if len(view_list) == 2:
    res = diffutils.DiffResults()
    comp = diffutils.compare_views(view_list[0], view_list[1], compare_types=__shiftclick__, diff_results=res)

    TaskDialog.Show('pyRevit', 'Views are smiliar (not identical).' if comp else 'Views are NOT smiliar.')

    if not comp:
        uidoc.ActiveView = view_list[0]
        selection.utils.replace_selection(res.diff_elements)
else:
    TaskDialog.Show('pyRevit', 'Exactly 2 views need to be selected.')
