"""Creates print set from selected views."""

from pyrevit import framework
from pyrevit import revit, DB, UI

sheetsetname = 'ViewPrintSet'

# Get printmanager / viewsheetsetting
printmanager = revit.doc.PrintManager
printmanager.PrintRange = DB.PrintRange.Select
viewsheetsetting = printmanager.ViewSheetSetting

# Collect selected views
myviewset = DB.ViewSet()
for el_id in revit.get_selection().element_ids:
    el = revit.doc.GetElement(el_id)
    if isinstance(el, DB.View):
        myviewset.Insert(el)

if myviewset.IsEmpty:
    UI.TaskDialog.Show('pyRevit', 'At least one view must be selected.')
else:
    # Collect existing sheet sets
    viewsheetsets = DB.FilteredElementCollector(revit.doc)\
                      .OfClass(framework.get_type(DB.ViewSheetSet))\
                      .WhereElementIsNotElementType()\
                      .ToElements()

    allviewsheetsets = {vss.Name: vss for vss in viewsheetsets}

    with revit.Transaction('Created Print Set'):
        # Delete existing matching sheet set
        if sheetsetname in allviewsheetsets.keys():
            viewsheetsetting.CurrentViewSheetSet = \
                allviewsheetsets[sheetsetname]
            viewsheetsetting.Delete()

        # Create new sheet set
        viewsheetsetting.CurrentViewSheetSet.Views = myviewset
        viewsheetsetting.SaveAs(sheetsetname)
