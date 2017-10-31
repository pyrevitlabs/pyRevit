from pyrevit.framework import List
from pyrevit import revit, DB, UI


__doc__ = 'Select a series of stacked walls. Run this tool and it '\
          'will replace the selection with sub-walls '\
          'of the selected stacked walls.'


selection = revit.get_selection()

sub_walls = []

for el in selection:
    if isinstance(el, DB.Wall):
        if el.IsStackedWall:
            sub_walls.extend(list(el.GetStackedWallMemberIds()))
        elif not el.IsStackedWall or el.IsStackedWallMember:
            sub_walls.append(el.Id)

if len(sub_walls) > 0:
    revit.uidoc.Selection.SetElementIds(List[DB.ElementId](sub_walls))
else:
    UI.TaskDialog.Show('pyRevit', 'Please select at least one Stacked wall.')
