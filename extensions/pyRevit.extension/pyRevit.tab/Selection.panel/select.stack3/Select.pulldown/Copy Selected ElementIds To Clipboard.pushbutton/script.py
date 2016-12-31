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

__doc__ = 'Copies the Elements Ids of the selected elements into the clipboard memory. You can then use ' \
          'Revit\'s own "Select By Id" tool, paste the Ids into the textbox from clipboard and ' \
          'click on the show button. For convenience this tool will call the "Select By Id" tool after copying.'


__window__.Close()
from Autodesk.Revit.UI import PostableCommand as pc
from Autodesk.Revit.UI import RevitCommandId as rcid
import os

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


def addtoclipboard(text):
    command = 'echo ' + text.strip() + '| clip'
    os.system(command)


selectedIds = ''

for elId in uidoc.Selection.GetElementIds():
    selectedIds = selectedIds + str(elId) + ','

cid_SelectById = rcid.LookupPostableCommandId(pc.SelectById)
addtoclipboard(selectedIds)
__revit__.PostCommand(cid_SelectById)
