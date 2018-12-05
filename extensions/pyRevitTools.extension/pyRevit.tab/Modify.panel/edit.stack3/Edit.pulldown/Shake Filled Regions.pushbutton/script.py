from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import script


__doc__ = 'Moves all Filled Regions on the seleced views back-and-forth by '\
          'a tiny amount to push Revit to regenerate the filled region and '\
          'update the display. This tool is meant to be used in '     \
          'conjunction with the "Swap Line Styles" tool. The swap tool '\
          'updates the line styles inside Filled region but does not '\
          'currently shake the filled regions (Revit crashes on large models.)'


output = script.get_output()
selection = revit.get_selection()


def shake_filled_regions(view):
    fregions = DB.FilteredElementCollector(revit.doc)\
                 .OwnedByView(view.Id)\
                 .OfClass(framework.get_type(DB.FilledRegion))\
                 .WhereElementIsNotElementType()\
                 .ToElements()

    print('Shaking Filled Regions in: {}'.format(view.ViewName))

    for i, fr in enumerate(fregions):
        with revit.Transaction('Shake Filled Region #{}'.format(i)):
            fr.Location.Move(DB.XYZ(0.01, 0, 0))
            fr.Location.Move(DB.XYZ(-0.01, 0, 0))


print('Shaking Filled Regions in {} views'.format(len(selection)))
with revit.TransactionGroup('Shake Filled Regions'):
    for i, view in enumerate(selection.elements):
        shake_filled_regions(view)
        output.update_progress(i+1, len(selection))

print('All Filled Regions where shaken...')
