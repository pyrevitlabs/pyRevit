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

__doc__ = 'Uses the Worksharing tooltip to find out the element creator and other info.'

__window__.Close()

from Autodesk.Revit.DB import WorksharingUtils, WorksharingTooltipInfo
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

if doc.IsWorkshared:
    if selection and len(selection) == 1:
        el = selection[0]
        wti = WorksharingUtils.GetWorksharingTooltipInfo(doc, el.Id)
        TaskDialog.Show('pyRevit',
                        'Creator: {0}\n'
                        'Current Owner: {1}\n'
                        'Last Changed By: {2}'.format(wti.Creator,
                                                      wti.Owner,
                                                      wti.LastChangedBy))
    else:
        TaskDialog.Show('pyRevit', 'Exactly one element must be selected.')
else:
    TaskDialog.Show('pyRevit', 'Model is not workshared.')
