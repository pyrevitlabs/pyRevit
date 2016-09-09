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

__doc__ = 'This is a tool to swap line styles. Run the tool, select a line with the style to be replaced, and then ' \
          'select a line with the source style. The script will correct the line styles in the model. ' \
          'HOWEVER the lines that are part of a group or a filled region will not be affected. ' \
          'Yeah I know. What\'s the point...But even this helps sometimes.'

from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory, ElementId
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
curview = doc.ActiveView

verbose = True

try:
    sel = []
    fromStyleLine = doc.GetElement(
        uidoc.Selection.PickObject(ObjectType.Element, 'Pick a line with the style to be replaced.'))
    fromStyle = fromStyleLine.LineStyle
    toStyleLine = doc.GetElement(uidoc.Selection.PickObject(ObjectType.Element, 'Pick a line with the source style.'))
    toStyle = toStyleLine.LineStyle

    linelist = []

    cl = FilteredElementCollector(doc)
    cllines = cl.OfCategory(BuiltInCategory.OST_Lines or BuiltInCategory.OST_SketchLines).WhereElementIsNotElementType()
    for c in cllines:
        if c.LineStyle.Name == fromStyle.Name:
            linelist.append(c)
        # print( '{0:<10} {1:<25}{2:<8} {3:<15}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name) )

    if len(linelist) > 100:
        verbose = False
    with Transaction(doc, 'Swap Line Styles') as t:
        t.Start()
        for line in linelist:
            if line.Category.Name != '<Sketch>' and line.GroupId < ElementId(0):
                if verbose:
                    print('LINE FOUND:\t{0:<10} {1:<25}{2:<8} {3:<15}'.format(line.Id,
                                                                              line.GetType().Name,
                                                                              line.LineStyle.Id,
                                                                              line.LineStyle.Name
                                                                              ))
                line.LineStyle = toStyle
            elif line.Category.Name == '<Sketch>':
                print('SKIPPED <Sketch> Line ----:\n'
                      '           \t{0:<10} {1:<25}{2:<8} {3:<15}\n'.format(line.Id,
                                                                            line.GetType().Name,
                                                                            line.LineStyle.Id,
                                                                            line.LineStyle.Name
                                                                            ))
            elif line.GroupId > ElementId(0):
                print('SKIPPED Grouped Line ----:\n'
                      '           \t{0:<10} {1:<25}{2:<8} {3:<15} {4:<10}\n'.format(line.Id,
                                                                                    line.GetType().Name,
                                                                                    line.LineStyle.Id,
                                                                                    line.LineStyle.Name,
                                                                                    doc.GetElement(line.GroupId).Name
                                                                                    ))

        t.Commit()
except:
    pass
