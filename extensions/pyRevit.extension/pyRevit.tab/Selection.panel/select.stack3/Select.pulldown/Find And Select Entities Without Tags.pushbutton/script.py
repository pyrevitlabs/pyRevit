"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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

__doc__ = 'Selects elements with no associated tags in current view.'

__window__.Close()

import sys
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ElementId, ViewSheet
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

import clr
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('WindowsBase')
import System.Windows

class commandSwitches:
    def __init__(self, switches, message = 'Pick a command option:'):
        # Create window
        self.my_window = System.Windows.Window()
        self.my_window.WindowStyle = System.Windows.WindowStyle.None
        self.my_window.AllowsTransparency = True
        self.my_window.Background = None
        self.my_window.Title = 'Command Options'
        self.my_window.Width = 600
        self.my_window.SizeToContent = System.Windows.SizeToContent.Height
        self.my_window.ResizeMode = System.Windows.ResizeMode.CanMinimize
        self.my_window.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen
        self.my_window.PreviewKeyDown += self.handleEsc
        border = System.Windows.Controls.Border()
        border.CornerRadius  = System.Windows.CornerRadius(15)
        border.Background = System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(220,55,50,50))
        self.my_window.Content = border

        # Create StackPanel to Layout UI elements
        stack_panel = System.Windows.Controls.StackPanel()
        stack_panel.Margin = System.Windows.Thickness(5)
        border.Child = stack_panel

        label = System.Windows.Controls.Label()
        label.Foreground = System.Windows.Media.Brushes.White
        label.Content = message
        label.Margin = System.Windows.Thickness(2, 0, 0, 0)
        stack_panel.Children.Add(label)

        # Create WrapPanel for command options
        self.button_list = System.Windows.Controls.WrapPanel()
        self.button_list.Margin = System.Windows.Thickness(5)
        stack_panel.Children.Add(self.button_list)

        for switch in switches:
            my_button = System.Windows.Controls.Button()
            my_button.BorderBrush = System.Windows.Media.Brushes.Black
            my_button.BorderThickness = System.Windows.Thickness(0)
            my_button.Content = switch
            my_button.Margin = System.Windows.Thickness(5, 0, 5, 5)
            my_button.Padding = System.Windows.Thickness(5, 0, 5, 0)
            my_button.Click += self.processSwitch
            self.button_list.Children.Add(my_button)


    def handleEsc(self, sender, args):
        if (args.Key == System.Windows.Input.Key.Escape):
            self.my_window.Close()


    def processSwitch(self, sender, args):
        self.my_window.Close()
        global selected_switch
        selected_switch = sender.Content

    def pickCommandSwitch(self):
        self.my_window.ShowDialog()


curview = uidoc.ActiveGraphicalView
if isinstance(curview, ViewSheet):
    TaskDialog.Show('pyrevit', "You're on a Sheet. Activate a model view please.")
    sys.exit(0)

selected_switch = ''

commandSwitches(['Rooms',
                 'Areas',
                 'Doors',
                 'Windows',
                 'Equipment',
                 'Walls',
                 ], 'Find untagged elements of type:').pickCommandSwitch()


if selected_switch == 'Rooms':
    roomtags = FilteredElementCollector(doc, curview.Id).OfCategory(
        BuiltInCategory.OST_RoomTags).WhereElementIsNotElementType().ToElementIds()
    rooms = FilteredElementCollector(doc, curview.Id).OfCategory(
        BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElementIds()

    taggedrooms = []
    untaggedrooms = []
    for rtid in roomtags:
        rt = doc.GetElement(rtid)
        if rt.Room is not None:
            taggedrooms.append(rt.Room.Number)

    for rmid in rooms:
        rm = doc.GetElement(rmid)
        if rm.Number not in taggedrooms:
            untaggedrooms.append(rmid)
            
    if len(untaggedrooms) > 0:
        uidoc.Selection.SetElementIds(List[ElementId](untaggedrooms))
    else:
        TaskDialog.Show('pyrevit', 'All rooms have associated tags.')

elif selected_switch == 'Areas':
    areatags = FilteredElementCollector(doc, curview.Id).OfCategory(
        BuiltInCategory.OST_AreaTags).WhereElementIsNotElementType().ToElementIds()
    areas = FilteredElementCollector(doc, curview.Id).OfCategory(
        BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElementIds()

    taggedareas = []
    untaggedareas = []
    for atid in areatags:
        at = doc.GetElement(atid)
        if at.Area is not None:
            taggedareas.append(at.Area.Id.IntegerValue)

    for areaid in areas:
        area = doc.GetElement(areaid)
        if area.Id.IntegerValue not in taggedareas:
            untaggedareas.append(areaid)

    if len(untaggedareas) > 0:
        uidoc.Selection.SetElementIds(List[ElementId](untaggedareas))
    else:
        TaskDialog.Show('pyrevit', 'All areas have associated tags.')

elif selected_switch == 'Doors' or selected_switch == 'Windows' or selected_switch == 'Walls':
    if selected_switch == 'Doors':
        tagcat = BuiltInCategory.OST_DoorTags
        elcat = BuiltInCategory.OST_Doors
        elname = 'doors'
    elif selected_switch == 'Windows':
        tagcat = BuiltInCategory.OST_WindowTags
        elcat = BuiltInCategory.OST_Windows
        elname = 'windows'
    elif selected_switch == 'Walls':
        tagcat = BuiltInCategory.OST_WallTags
        elcat = BuiltInCategory.OST_Walls
        elname = 'Walls'


    elementtags = FilteredElementCollector(doc, curview.Id).OfCategory(tagcat) \
        .WhereElementIsNotElementType().ToElementIds()
    elements = FilteredElementCollector(doc, curview.Id).OfCategory(elcat) \
        .WhereElementIsNotElementType().ToElementIds()

    tagged_elements = []
    untagged_elements = []
    for eltid in elementtags:
        elt = doc.GetElement(eltid)
        if elt.TaggedLocalElementId != ElementId.InvalidElementId:
            tagged_elements.append(elt.TaggedLocalElementId.IntegerValue)

    for elid in elements:
        el = doc.GetElement(elid)
        try:
            typecomment = el.Symbol.LookupParameter('Type Comments')
            if el.Id.IntegerValue not in tagged_elements and \
                typecomment and typecomment.HasValue and ('auxiliary' not in typecomment.AsString().lower()):
                untagged_elements.append(elid)
        except:
            if el.Id.IntegerValue not in tagged_elements:
                untagged_elements.append(elid)

    if len(untagged_elements) > 0:
        uidoc.Selection.SetElementIds(List[ElementId](untagged_elements))
    else:
        TaskDialog.Show('pyrevit', 'All {} have associated tags.'.format(elname))

