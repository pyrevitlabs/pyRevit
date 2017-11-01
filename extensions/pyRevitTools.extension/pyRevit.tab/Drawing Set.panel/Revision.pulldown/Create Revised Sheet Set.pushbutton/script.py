from pyrevit import framework
from pyrevit.framework import Windows
from pyrevit import revit, DB


__doc__ = 'Select a revision from the list of revisions and this script '\
          'will create a print sheet set for the revised sheets under the '\
          'selected revision, and will assign the new sheet set as '\
          'the default print set.'


class RevisionSelectorWindow:
    def __init__(self):
        # Create window
        self.my_window = Windows.Window()
        self.my_window.Title = 'Select Revision:'
        self.my_window.Width = 600
        self.my_window.Height = 200
        self.my_window.ResizeMode = Windows.ResizeMode.CanMinimize

        # Create StackPanel to Layout UI elements
        self.my_stack = Windows.Controls.StackPanel()
        self.my_stack.Margin = Windows.Thickness(5)
        self.my_window.Content = self.my_stack

        self.my_listView_revisionList = Windows.Controls.ListView()
        self.my_listView_revisionList.Height = 115

        self.my_button_createSheetSet = Windows.Controls.Button()
        self.my_button_createSheetSet.Content = 'Create Sheet Set'
        self.my_button_createSheetSet.Margin = Windows.Thickness(30, 10, 30, 0)
        self.my_button_createSheetSet.Click += self.createsheetset

        self.my_stack.Children.Add(self.my_listView_revisionList)
        self.my_stack.Children.Add(self.my_button_createSheetSet)

        # collect data:
        allrevsnotsorted = DB.FilteredElementCollector(revit.doc).OfCategory(
            DB.BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()
        allRevs = sorted(allrevsnotsorted, key=lambda x: x.RevisionNumber)
        self.revs = [x.Id.IntegerValue for x in allRevs]

        for rev in allRevs:
            self.my_listView_revisionList.AddText(
                '{0} {1} {2}'.format(str(rev.RevisionNumber).ljust(10),
                                     str(rev.Description).ljust(50),
                                     rev.RevisionDate))

    def createsheetset(self, sender, args):
        self.my_window.Close()
        # get selected revision
        srindex = self.my_listView_revisionList.SelectedIndex
        if srindex >= 0:
            sr = revit.doc.GetElement(DB.ElementId(self.revs[srindex]))
        else:
            return

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
        sheetsetname = 'Rev {0}: {1}'.format(sr.RevisionNumber, sr.Description)

        with revit.Transaction('Create Revision Sheet Set'):
            if sheetsetname in allviewsheetsets.keys():
                viewsheetsetting.CurrentViewSheetSet = \
                    allviewsheetsets[sheetsetname]
                viewsheetsetting.Delete()

            # find revised sheets
            myviewset = DB.ViewSet()
            for s in sheets:
                revs = s.GetAllRevisionIds()
                revids = [x.IntegerValue for x in revs]
                if sr.Id.IntegerValue in revids:
                    myviewset.Insert(s)

            # create new sheet set
            viewsheetsetting.CurrentViewSheetSet.Views = myviewset
            viewsheetsetting.SaveAs(sheetsetname)

    def show(self):
        self.my_window.ShowDialog()


RevisionSelectorWindow().show()
