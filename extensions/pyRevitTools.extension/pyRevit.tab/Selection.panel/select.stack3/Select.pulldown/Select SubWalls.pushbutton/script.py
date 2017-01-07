__doc__ = 'Select a series of stacked walls. Run this tool and it will replace the selection with sub-walls ' \
          'of the selected stacked walls.'

from Autodesk.Revit.DB import ElementId, Wall
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(uidoc.Selection.GetElementIds())

sub_walls = []

for elid in selection:
    el = doc.GetElement(elid)
    if isinstance(el, Wall):
        if el.IsStackedWall:
            sub_walls.extend(list(el.GetStackedWallMemberIds()))
        elif not el.IsStackedWall or el.IsStackedWallMember:
            sub_walls.append(elid)

if len(sub_walls) > 0:
    uidoc.Selection.SetElementIds(List[ElementId](sub_walls))
else:
    TaskDialog.Show('pyRevit', 'Please select at least one Stacked wall.')
