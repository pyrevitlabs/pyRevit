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

__doc__ = 'Exports selected schedules to TXT files on user desktop'

from Autodesk.Revit.DB import ViewSchedule, ViewScheduleExportOptions, ExportColumnHeaders, ExportTextQualifier
import os
import os.path as op

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

desktop = op.expandvars('%userprofile%\\desktop')

vseop = ViewScheduleExportOptions()
# vseop.ColumnHeaders = ExportColumnHeaders.None
# vseop.TextQualifier = ExportTextQualifier.None
# vseop.FieldDelimiter = ','
# vseop.Title = False

for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    fname = "".join(x for x in el.ViewName if x not in ['*']) + '.txt'
    el.Export(desktop, fname, vseop)
    print('EXPORTED: {0}\n      TO: {1}\n'.format(el.ViewName, fname))
