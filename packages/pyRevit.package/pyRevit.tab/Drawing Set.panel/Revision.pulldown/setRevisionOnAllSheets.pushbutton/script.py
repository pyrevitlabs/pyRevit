"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Select a revision from the list of revisions and this script set that revision on ' \
          'all sheets in the model as an additional revision.'

__window__.Hide()

import clr

clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('System.Data')
import System.Windows
import System.Data
from System.Collections.Generic import List

from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory, ElementId, PrintRange, ViewSet, \
    ViewSheetSet

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


class RevisionSelectorWindow:
    def __init__(self):
        # Create window
        self.my_window = System.Windows.Window()
        self.my_window.Title = 'Select Revision:'
        self.my_window.Width = 600
        self.my_window.Height = 200
        self.my_window.ResizeMode = System.Windows.ResizeMode.CanMinimize

        # Create StackPanel to Layout UI elements
        self.my_stack = System.Windows.Controls.StackPanel()
        self.my_stack.Margin = System.Windows.Thickness(5)
        self.my_window.Content = self.my_stack

        self.my_listView_revisionList = System.Windows.Controls.ListView()
        self.my_listView_revisionList.Height = 115

        self.my_button_createSheetSet = System.Windows.Controls.Button()
        self.my_button_createSheetSet.Content = 'Set Revision on All Sheets'
        self.my_button_createSheetSet.Margin = System.Windows.Thickness(30, 10, 30, 0)
        self.my_button_createSheetSet.Click += self.createsheetset

        self.my_stack.Children.Add(self.my_listView_revisionList)
        self.my_stack.Children.Add(self.my_button_createSheetSet)

        # collect data:
        allrevsnotsorted = FilteredElementCollector(doc).OfCategory(
            BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()
        allrevs = sorted(allrevsnotsorted, key=lambda x: x.RevisionNumber)
        self.revs = [x.Id.IntegerValue for x in allrevs]

        for rev in allrevs:
            self.my_listView_revisionList.AddText(
                '{0} {1} {2}'.format(str(rev.RevisionNumber).ljust(10), str(rev.Description).ljust(50),
                                     rev.RevisionDate))

    def createsheetset(self, sender, args):
        self.my_window.Close()
        __window__.Show()
        # get selected revision
        srindex = self.my_listView_revisionList.SelectedIndex
        if srindex >= 0:
            sr = doc.GetElement(ElementId(self.revs[srindex]))
        else:
            return

        # collect data
        sheets = FilteredElementCollector(doc).OfCategory(
            BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
        affectedsheets = []
        with Transaction(doc, 'Set Revision on Sheets') as t:
            t.Start()
            for s in sheets:
                revs = list(s.GetAdditionalRevisionIds())
                revs.append(sr.Id)
                s.SetAdditionalRevisionIds(List[ElementId](revs))
                affectedsheets.append(s)
            t.Commit()
        if len(affectedsheets) > 0:
            print('SELECTED REVISION ADDED TO THESE SHEETS:')
            print('-' * 100)
            for s in affectedsheets:
                print('NUMBER: {0}   NAME:{1}'.format(s.LookupParameter('Sheet Number').AsString().rjust(10),
                                                      s.LookupParameter('Sheet Name').AsString().ljust(50)
                                                      ))

    def showwindow(self):
        self.my_window.ShowDialog()


RevisionSelectorWindow().showwindow()
