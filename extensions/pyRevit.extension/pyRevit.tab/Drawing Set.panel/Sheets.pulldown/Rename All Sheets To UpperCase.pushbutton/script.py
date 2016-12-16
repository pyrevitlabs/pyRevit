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

__doc__ = 'Renames all sheets to UPPERCASE.'

from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(views, key=lambda x: x.SheetNumber)

t = Transaction(doc, 'Rename Sheets to Upper')
t.Start()

for el in sheets:
    sheetnameparam = el.LookupParameter('Sheet Name')
    name = sheetnameparam.AsString()
    name = name.upper()
    print('RENAMING:\t{0}\n'
          '      to:\t{1}\n'.format(name, name.upper()))
    sheetnameparam.Set(name)

t.Commit()
