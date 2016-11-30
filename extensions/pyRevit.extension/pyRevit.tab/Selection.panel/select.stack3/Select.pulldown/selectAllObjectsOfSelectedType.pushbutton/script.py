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

__doc__ = 'Select all elements of the same type as selected element and reports their ' \
          'IDs (sorted by the owner view if they are View Specific objects)'

# Select a filled region first and run this.
# this script will select all elements matching the type of the selected filled region
from Autodesk.Revit.DB import FilteredElementCollector
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

if len(selection) > 0:
    firstEl = selection[0]
    CID = firstEl.Category.Id
    TID = firstEl.GetTypeId()

    cl = FilteredElementCollector(doc)
    catlist = cl.OfCategoryId(CID).WhereElementIsNotElementType().ToElements()

    filteredlist = []
    modelItems = []
    vsItems = {}
    vsList = firstEl.ViewSpecific

    for r in catlist:
        if r.GetTypeId() == TID:
            filteredlist.append(r.Id)
            if vsList:
                ovname = doc.GetElement(r.OwnerViewId).ViewName
                if ovname in vsItems:
                    vsItems[ovname].append(r)
                else:
                    vsItems[ovname] = [r]
            else:
                modelItems.append(r)

    if vsList:
        for ovname, items in vsItems.items():
            print('OWNER VIEW: {0}'.format(ovname))
            for r in items:
                print('\tID: {0}\t{1}'.format(r.Id,
                                              r.GetType().Name.ljust(20)
                                              ))
            print('\n')
    else:
        print('SELECTING MODEL ITEMS:')
        for el in modelItems:
            print('\tID: {0}\t{1}'.format(r.Id,
                                          r.GetType().Name.ljust(20)
                                          ))

    uidoc.Selection.SetElementIds(List[ElementId](filteredlist))
else:
    __window__.Close()
    TaskDialog.Show('pyrevit', 'At least one object must be selected.')
