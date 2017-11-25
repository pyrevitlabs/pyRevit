from pyrevit.framework import List, Windows
from pyrevit import revit, DB


__doc__ = 'Selects all revision clouds of a sepecific revision. '\
          'This is helpful for setting a parameter or comment ' \
          'on all the revision clouds at once.'


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
        self.my_button_createSheetSet.Content = 'Select All Revision Clouds'
        self.my_button_createSheetSet.Margin = Windows.Thickness(30, 10, 30, 0)
        self.my_button_createSheetSet.Click += self.select_clouds

        self.my_stack.Children.Add(self.my_listView_revisionList)
        self.my_stack.Children.Add(self.my_button_createSheetSet)

        # collect data:
        allrevsnotsorted = DB.FilteredElementCollector(revit.doc)\
                             .OfCategory(DB.BuiltInCategory.OST_Revisions)\
                             .WhereElementIsNotElementType()
        allRevs = sorted(allrevsnotsorted, key=lambda x: x.RevisionNumber)
        self.revs = [x.Id.IntegerValue for x in allRevs]

        for rev in allRevs:
            self.my_listView_revisionList.AddText(
                '{0} {1} {2}'.format(str(rev.RevisionNumber).ljust(10),
                                     str(rev.Description).ljust(50),
                                     rev.RevisionDate))

    def select_clouds(self, sender, args):
        self.my_window.Close()
        cl = DB.FilteredElementCollector(revit.doc)
        revclouds = cl.OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
                      .WhereElementIsNotElementType()

        # get selected revision
        srindex = self.my_listView_revisionList.SelectedIndex
        if srindex >= 0:
            sr = revit.doc.GetElement(DB.ElementId(self.revs[srindex]))
        else:
            return

        clouds = []

        for revcloud in revclouds:
            if revcloud.RevisionId.IntegerValue == sr.Id.IntegerValue:
                clouds.append(revcloud.Id)

        revit.get_selection().set_to(clouds)

    def showwindow(self):
        self.my_window.ShowDialog()


RevisionSelectorWindow().showwindow()
