"""Toggle all/selected grid bubbles in the active view."""
#pylint: disable=E0401
from pyrevit import forms
from pyrevit import revit, DB


__min_revit_ver__ = 2016


all_grids = DB.FilteredElementCollector(revit.doc)\
              .OfCategory(DB.BuiltInCategory.OST_Grids)\
              .WhereElementIsNotElementType().ToElements()

selected_option = \
        forms.CommandSwitchWindow.show(
            ['Show Bubbles',
             'Hide Bubbles'],
            message='Select option:'
            )

if selected_option:
    hide = True
    if selected_option == 'Show Bubbles':
        hide = False
    
    grids = []
    selection = revit.get_selection()
    if selection:
        grids = [x for x in selection if isinstance(x, DB.Grid)]
    else:
        grids = all_grids
    
    try:
        with revit.Transaction('Toggle Grid Bubbles'):
            for grid in grids:
                if hide:
                    grid.HideBubbleInView(DB.DatumEnds.End0, revit.active_view)
                    grid.HideBubbleInView(DB.DatumEnds.End1, revit.active_view)
                else:
                    grid.ShowBubbleInView(DB.DatumEnds.End0, revit.active_view)
                    grid.ShowBubbleInView(DB.DatumEnds.End1, revit.active_view)

    except Exception:
        pass

    revit.uidoc.RefreshActiveView()
