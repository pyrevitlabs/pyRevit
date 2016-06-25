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

__doc__ = 'Lists all sheets revised under any revision.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

doc = __revit__.ActiveUIDocument.Document

print('LIST OF REVISIONS:')
cl = FilteredElementCollector(doc)
revs = cl.OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()
for rev in revs:
    print('{0}\tREV#: {1}DATE: {2}TYPE:{3}DESC: {4}'.format(rev.SequenceNumber, str(rev.RevisionNumber).ljust(5),
                                                            str(rev.RevisionDate).ljust(10),
                                                            str(rev.NumberType.ToString()).ljust(15), rev.Description))

print('\n\n'
      'REVISED SHEETS:\n'
      '\n'
      'NAME\tNUMBER\n--------------------------------------------------------------------------')

sheetsnotsorted = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for sht in sheets:
    revs = sht.GetAllRevisionIds()
    if len(revs) > 0:
        print('{0}\t{1}'.format(sht.LookupParameter('Sheet Number').AsString(),
                                sht.LookupParameter('Sheet Name').AsString()
                                ))
        for rev in revs:
            rev = doc.GetElement(rev)
            print('\tREV#: {0}\t\tDATE: {1}\t\tDESC:{2}'.format(rev.RevisionNumber,
                                                                rev.RevisionDate,
                                                                rev.Description
                                                                ))
