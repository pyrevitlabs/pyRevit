#pylint: disable=missing-docstring,import-error,invalid-name,unused-argument
from pyrevit import revit, DB
from pyrevit import script

__doc__ = 'Moves all Filled Regions on the seleced views back-and-forth by '\
          'a tiny amount to push Revit to regenerate the filled region and '\
          'update the display. This tool is meant to be used in '     \
          'conjunction with the "Convert Line Styles" tool. The convert tool '\
          'updates the line styles inside Filled region but does not '\
          'currently shake the filled regions (Revit crashes on large models.)'


output = script.get_output()

# collect target views
selection = revit.get_selection()
target_views = selection.elements
if not target_views:
    target_views = [revit.active_view]


def shake_filled_regions(target_view):
    filled_regions = \
        DB.FilteredElementCollector(target_view.Document, target_view.Id)\
          .OfClass(DB.FilledRegion)\
          .WhereElementIsNotElementType()\
          .ToElements()

    print('Shaking Filled Regions in: {}'
          .format(revit.query.get_name(target_view)))

    for fregion in filled_regions:
        with revit.Transaction('Shake Filled Region'):
            fregion.Location.Move(DB.XYZ(0.1, 0, 0))
            fregion.Location.Move(DB.XYZ(-0.1, 0, 0))


print('Shaking Filled Regions in {} views'.format(len(target_views)))
with revit.TransactionGroup('Shake Filled Regions'):
    for idx, view in enumerate(target_views):
        shake_filled_regions(view)
        output.update_progress(idx+1, len(target_views))

print('All Filled Regions where shaken...')
