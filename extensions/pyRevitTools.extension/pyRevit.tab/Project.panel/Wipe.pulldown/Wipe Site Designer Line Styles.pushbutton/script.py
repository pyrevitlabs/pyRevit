"""Deletes all extra lines styles created by the faulty Site Designer addin."""

import StringIO

from pyrevit.framework import List
from pyrevit import revit, DB


outputs = StringIO.StringIO()
catsToDelete = []


def report(message):
    outputs.write(message)
    outputs.write('\n')


# COLLECT CATS - METHOD 1
report('Finding Line Styles using Method 1...')
linesCat = revit.doc.Settings.Categories.get_Item("Lines")
for cat in linesCat.SubCategories:
    if 'SW' == cat.Name[:2]:
        catsToDelete.append(cat)

# COLLECT CATS - METHOD 2
report('Finding Line Styles using Method 2...')
emcfilter = \
    DB.ElementMulticategoryFilter(
        List[DB.BuiltInCategory]([DB.BuiltInCategory.OST_Lines])
        )

cllines = list(DB.FilteredElementCollector(revit.doc)
                 .WherePasses(emcfilter)
                 .WhereElementIsNotElementType()
                 .ToElements())

if cllines:
    styleIds = cllines[0].GetLineStyleIds()

    for styleId in styleIds:
        style = revit.doc.GetElement(styleId)
        cat = style.GraphicsStyleCategory
        if 'SW' == cat.Name[:2]:
            catsToDelete.append(cat)

    # DELETE CATS
    total = len(catsToDelete)
    report('Deleting {0} Line Styles...'.format(total))
    report('Deleted Line Styles:')
    step = 1 / 50.0
    threshold = step

    with revit.Transaction('Delete all SW Lines'):
        for i, cat in enumerate(catsToDelete):
            try:
                report('ID: {0}\tNAME: {1}'.format(cat.Id, cat.Name))
                revit.doc.Delete(cat.Id)
                if i / float(total) >= threshold:
                    report('|', end='')
                    threshold += step
            except Exception:
                continue

    report('\n\n')
    print(outputs.getvalue())
