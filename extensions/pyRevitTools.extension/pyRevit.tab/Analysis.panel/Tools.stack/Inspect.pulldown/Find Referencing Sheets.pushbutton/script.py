"""Find all sheets referencing the current view.
Especially useful for finding legends.
"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"

output = script.get_output()

curview = revit.active_view
count = 0


print('Searching All Sheets for {} {}\n'
      .format(curview.Name, output.linkify(curview.Id)))

for sheet in revit.query.get_sheets(include_placeholders=False):
    vps_ids = [revit.doc.GetElement(x).ViewId for x in sheet.GetAllViewports()]
    curviewelements = DB.FilteredElementCollector(revit.doc)\
                        .OwnedByView(sheet.Id)\
                        .WhereElementIsNotElementType()\
                        .ToElements()

    for el in curviewelements:
        if isinstance(el, DB.ScheduleSheetInstance):
            vps_ids.append(el.ScheduleId)

    if curview.Id in vps_ids:
        count += 1
        revit.report.print_sheet(sheet)

print('\n\nView is referenced on {0} sheets.'.format(count))
