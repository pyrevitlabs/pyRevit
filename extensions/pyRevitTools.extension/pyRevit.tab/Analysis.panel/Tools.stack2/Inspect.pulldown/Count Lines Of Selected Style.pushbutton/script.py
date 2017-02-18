"""Counts all lines in the model with matching style to the selected line.

CTRL-Click: Lists every matching line
"""

from scriptutils import logger
from revitutils import doc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory


cl = FilteredElementCollector(doc)
cllines = cl.OfCategory(BuiltInCategory.OST_Lines or BuiltInCategory.OST_SketchLines).WhereElementIsNotElementType()

for selected_line in selection.elements:
    selectedStyle = selected_line.LineStyle

    count = 0
    for c in cllines:
        if c.LineStyle.Name == selectedStyle.Name:
            logger.debug('{0:<10} {1:<25}{2:<8} {3:<15}'.format(c.Id,
                                                                c.GetType().Name,
                                                                c.LineStyle.Id,
                                                                c.LineStyle.Name))
            count += 1

    print('There are {} lines of style <{}> in the model.'.format(count, selectedStyle.Name))
