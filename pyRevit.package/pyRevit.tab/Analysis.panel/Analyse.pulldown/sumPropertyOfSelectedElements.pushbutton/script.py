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

__doc__ = 'Sums up the values of selected parameter on selected elements. Elements not containig ' \
          'that parameter will be skipped.'

__window__.Hide()

from Autodesk.Revit.DB import CurveElement

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

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

commandSwitches(['Length',
                 'Perimeter',
                 'Area',
                 'Volume',
                 ], 'Sum values of parameter:').pickCommandSwitch()

total = 0.0

if selected_switch is not '':
    __window__.Show()
else:
    __window__.Close()

if selected_switch == 'Length':
    def isline(line):
        return isinstance(line, CurveElement)

    lines = []

    print("PROCESSING TOTAL OF {0} OBJECTS:\n\n".format(len(selection)))

    for i, el in enumerate(selection):
        if isline(el):
            lines.append(el)
        total += el.LookupParameter('Length').AsDouble()
    print("TOTAL LENGTH OF ALL SELECTED LINES IS: {0}\n\n\n".format(total))

    # group lines per line style
    linestyles = {}
    for l in lines:
        if l.LineStyle.Name in linestyles:
            linestyles[l.LineStyle.Name].append(l)
        else:
            linestyles[l.LineStyle.Name] = [l]

    for k in sorted(linestyles.keys()):
        linestyletotal = 0.0
        for l in linestyles[k]:
            linestyletotal += l.LookupParameter('Length').AsDouble()
        print("- LINES OF STYLE: {0} -\nTOTAL LENGTH : {1}\n\n".format(k, linestyletotal))

elif selected_switch == 'Perimeter':
    for el in selection:
        param = el.LookupParameter('Perimeter')
        if param:
            total += el.LookupParameter('Perimeter').AsDouble()
        else:
            print('Elemend with ID: {0} does not have Perimeter parameter.'.format(el.Id))
    print("TOTAL PERIMETER OF ALL SELECTED ELEMENTS IS: {0}".format(total))

elif selected_switch == 'Area':
    for el in selection:
        param = el.LookupParameter('Area')
        if param:
            total += el.LookupParameter('Area').AsDouble()
        else:
            print('Elemend with ID: {0} does not have Area parameter.'.format(el.Id))
    print("TOTAL AREA OF ALL SELECTED ELEMENTS IS:\n{0} SQFT\n{1} ACRE".format(total, total / 43560))

elif selected_switch == 'Volume':
    for el in selection:
        param = el.LookupParameter('Volume')
        if param:
            total += el.LookupParameter('Volume').AsDouble()
        else:
            print('Elemend with ID: {0} does not have Volume parameter.'.format(el.Id))
    print("TOTAL VOLUME OF ALL SELECTED ELEMENTS IS: {0}".format(total))
