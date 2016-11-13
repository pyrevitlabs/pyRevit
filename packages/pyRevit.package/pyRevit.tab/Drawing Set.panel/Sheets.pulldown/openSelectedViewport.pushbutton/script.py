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

__doc__ = 'Opens the view associated to the selected viewport. You can assign a shortcut to this tool ' \
          'and this is a quick way top open the views when working on sheets.'

__window__.Close()

from Autodesk.Revit.DB import Viewport
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

# Opens the associated view with the selected viewport on a sheet.
if len(selection) > 0 and isinstance(selection[0], Viewport):
    vp = selection[0]
    vpid = vp.ViewId
    view = doc.GetElement(vpid)
    uidoc.ActiveView = view
else:
    TaskDialog.Show('pyrevit', 'Select a Viewport first')
