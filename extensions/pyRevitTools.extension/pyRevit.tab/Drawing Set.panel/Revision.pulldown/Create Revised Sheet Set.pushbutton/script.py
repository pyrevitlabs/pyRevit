from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms


__doc__ = 'Select a revision from the list of revisions and this script '\
          'will create a print sheet set for the revised sheets under the '\
          'selected revision, and will assign the new sheet set as '\
          'the default print set.'


def createsheetset(revision_element):
    # get printed printmanager
    printmanager = revit.doc.PrintManager
    printmanager.PrintRange = DB.PrintRange.Select
    viewsheetsetting = printmanager.ViewSheetSetting

    # collect data
    sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
                        .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                        .WhereElementIsNotElementType()\
                        .ToElements()

    sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
    viewsheetsets = DB.FilteredElementCollector(revit.doc)\
                      .OfClass(framework.get_type(DB.ViewSheetSet))\
                      .WhereElementIsNotElementType()\
                      .ToElements()

    allviewsheetsets = {vss.Name: vss for vss in viewsheetsets}
    revnum = revision_element.SequenceNumber
    if hasattr(revision_element, 'RevisionNumber'):
        revnum = revision_element.RevisionNumber
    sheetsetname = 'Rev {0}: {1}'.format(revnum,
                                         revision_element.Description)

    with revit.Transaction('Create Revision Sheet Set'):
        if sheetsetname in allviewsheetsets.keys():
            viewsheetsetting.CurrentViewSheetSet = \
                allviewsheetsets[sheetsetname]
            viewsheetsetting.Delete()

        # find revised sheets
        myviewset = DB.ViewSet()
        for sheet in sheets:
            revs = sheet.GetAllRevisionIds()
            revids = [x.IntegerValue for x in revs]
            if revision_element.Id.IntegerValue in revids:
                myviewset.Insert(sheet)

        # create new sheet set
        viewsheetsetting.CurrentViewSheetSet.Views = myviewset
        viewsheetsetting.SaveAs(sheetsetname)


revision = forms.select_revisions(button_name='Create Sheet Set',
                                  multiselect=False)
if revision:
    createsheetset(revision)
