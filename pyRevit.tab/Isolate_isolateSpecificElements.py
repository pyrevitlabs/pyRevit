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

__doc__ = 'Isolates specific elements in current view and put the view in isolate element mode.'

__window__.Close()

from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory, Group, ElementId, Wall, \
                              Dimension
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

selected_switch = ''

elementCat = { 'Area Lines':BuiltInCategory.OST_AreaSchemeLines,
               'Doors':BuiltInCategory.OST_Doors,
               'Room Separation Lines':BuiltInCategory.OST_RoomSeparationLines,
               'Room Tags':None,
               'Model Groups':None,
               'Painted Elements':None,
               'Model Elements': None,
             }

commandSwitches(sorted(elementCat.keys()), 'Temporarily isolate elements of type:').pickCommandSwitch()

if selected_switch is not '':
    curview = uidoc.ActiveGraphicalView
    if selected_switch == 'Room Tags':
        roomtags = FilteredElementCollector(doc, curview.Id).OfCategory(
            BuiltInCategory.OST_RoomTags).WhereElementIsNotElementType().ToElementIds()
        rooms = FilteredElementCollector(doc, curview.Id).OfCategory(
            BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElementIds()

        allelements = []
        allelements.extend(rooms)
        allelements.extend(roomtags)
        element_to_isolate = List[ElementId](allelements)

    elif selected_switch == 'Model Groups':
        elements = FilteredElementCollector(doc, curview.Id).WhereElementIsNotElementType().ToElementIds()

        modelgroups = []
        expanded = []
        for elid in elements:
            el = doc.GetElement(elid)
            if isinstance(el, Group) and not el.ViewSpecific:
                modelgroups.append(elid)
                members = el.GetMemberIds()
                expanded.extend(list(members))

        expanded.extend(modelgroups)
        element_to_isolate = List[ElementId](expanded)

    elif selected_switch == 'Painted Elements':
        set = []
        elements = FilteredElementCollector(doc, curview.Id).WhereElementIsNotElementType().ToElementIds()
        for elId in elements:
            el = doc.GetElement(elId)
            if len(list(el.GetMaterialIds(True))) > 0:
                set.append(elId)
            elif isinstance(el, Wall) and el.IsStackedWall:
                memberWalls = el.GetStackedWallMemberIds()
                for mwid in memberWalls:
                    mw = doc.GetElement(mwid)
                    if len(list(mw.GetMaterialIds(True))) > 0:
                        set.append(elId)
        element_to_isolate = List[ElementId](set)

    elif selected_switch == 'Model Elements':
        elements = FilteredElementCollector(doc, curview.Id).WhereElementIsNotElementType().ToElementIds()

        element_to_isolate = []
        for elid in elements:
            el = doc.GetElement(elid)
            if not el.ViewSpecific:  #and not isinstance(el, Dimension):
                element_to_isolate.append(elid)

        element_to_isolate = List[ElementId](element_to_isolate)

    else:
        element_to_isolate = FilteredElementCollector(doc, curview.Id).OfCategory(
            elementCat[selected_switch]).WhereElementIsNotElementType().ToElementIds()

    t = Transaction(doc, 'Isolate {}'.format(selected_switch))
    t.Start()

    curview.IsolateElementsTemporary(element_to_isolate)

    t.Commit()
