from pyrevit.framework import Windows, List
from pyrevit import revit, DB


__doc__ = 'Select a revision from the list of revisions and '\
          'this script set that revision on all sheets in the '\
          'model as an additional revision.'


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
        self.my_button_createSheetSet.Content = 'Set Revision on All Sheets'
        self.my_button_createSheetSet.Margin = Windows.Thickness(30, 10, 30, 0)
        self.my_button_createSheetSet.Click += self.createsheetset

        self.my_stack.Children.Add(self.my_listView_revisionList)
        self.my_stack.Children.Add(self.my_button_createSheetSet)

        # collect data:
        allrevsnotsorted = DB.FilteredElementCollector(revit.doc)\
                             .OfCategory(DB.BuiltInCategory.OST_Revisions)\
                             .WhereElementIsNotElementType()

        allrevs = sorted(allrevsnotsorted, key=lambda x: x.RevisionNumber)
        self.revs = [x.Id.IntegerValue for x in allrevs]

        for rev in allrevs:
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

        # collect data
        sheets = DB.FilteredElementCollector(revit.doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

        affectedsheets = []
        with revit.Transaction('Set Revision on Sheets'):
            for s in sheets:
                revs = list(s.GetAdditionalRevisionIds())
                revs.append(sr.Id)
                s.SetAdditionalRevisionIds(List[DB.ElementId](revs))
                affectedsheets.append(s)

        if len(affectedsheets) > 0:
            print('SELECTED REVISION ADDED TO THESE SHEETS:')
            print('-' * 100)
            for s in affectedsheets:
                snum = s.LookupParameter('Sheet Number').AsString().rjust(10)
                sname = s.LookupParameter('Sheet Name').AsString().ljust(50)
                print('NUMBER: {0}   NAME:{1}'.format(snum, sname))

    def show(self):
        self.my_window.ShowDialog()


RevisionSelectorWindow().show()
