import clr

from scriptutils import this_script
from revitutils import doc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, FilteredElementCollector, FilledRegion, XYZ, TransactionGroup


__doc__ = 'Moves all Filled Regions on the seleced views back-and-forth by a tiny amount to push Revit '  \
          'to regenerate the filled region and update the display. This tool is meant to be used in '     \
          'conjunction with the "Swap Line Styles" tool. The swap tool updates the line styles inside '   \
          'Filled region but does not currently shake the filled regions (Revit crashes on large models.)'


def shake_filled_regions(view):
    vcl = FilteredElementCollector(doc).OwnedByView(view.Id)
    fregions = vcl.OfClass(clr.GetClrType(FilledRegion)).WhereElementIsNotElementType().ToElements()

    print('Shaking Filled Regions in: {}'.format(view.ViewName))

    for i, fr in enumerate(fregions):
        with Transaction(doc, 'Shake FilledRegion #{}'.format(i)) as t:
            t.Start()
            fr.Location.Move(XYZ(0.01, 0, 0))
            fr.Location.Move(XYZ(-0.01, 0, 0))
            t.Commit()


print('Shaking Filled Regions in {} views'.format(len(selection)))
with TransactionGroup(doc, 'Shake Filled Regions') as t:
    t.Start()
    for i, view in enumerate(selection.elements):
        shake_filled_regions(view)
        this_script.output.update_progress(i+1, len(selection))
    t.Assimilate()

print('All Filled Regions where shaken...')
