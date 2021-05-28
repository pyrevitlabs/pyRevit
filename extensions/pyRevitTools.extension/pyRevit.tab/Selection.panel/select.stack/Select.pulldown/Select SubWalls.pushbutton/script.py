from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()

sub_walls = []

for el in selection:
    if isinstance(el, DB.Wall):
        if el.IsStackedWall:
            sub_walls.extend(list(el.GetStackedWallMemberIds()))
        elif not el.IsStackedWall or el.IsStackedWallMember:
            sub_walls.append(el.Id)

if len(sub_walls) > 0:
    selection.set_to(sub_walls)
else:
    forms.alert('Please select at least one Stacked wall.')
