import clr

from Autodesk.Revit.DB import Transaction, FilteredElementCollector, PrintRange, View, ViewSet, ViewSheetSet
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

sheetsetname = 'ViewPrintSet'

# Get printmanager / viewsheetsetting
printmanager = doc.PrintManager
printmanager.PrintRange = PrintRange.Select
viewsheetsetting = printmanager.ViewSheetSetting

# Collect selected views
myviewset = ViewSet()
for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    if isinstance(el, View):
        myviewset.Insert(el)

if myviewset.IsEmpty:
    TaskDialog.Show('pyRevit', 'At least one view must be selected.')
else:
    # Collect existing sheet sets
    cl = FilteredElementCollector(doc)
    viewsheetsets = cl.OfClass(clr.GetClrType(ViewSheetSet)).WhereElementIsNotElementType().ToElements()
    allviewsheetsets = {vss.Name: vss for vss in viewsheetsets}

    with Transaction(doc, 'Created Print Set') as t:
        t.Start()
        # Delete existing matching sheet set
        if sheetsetname in allviewsheetsets.keys():
            viewsheetsetting.CurrentViewSheetSet = allviewsheetsets[sheetsetname]
            viewsheetsetting.Delete()

        # Create new sheet set
        viewsheetsetting.CurrentViewSheetSet.Views = myviewset
        viewsheetsetting.SaveAs(sheetsetname)
        t.Commit()
