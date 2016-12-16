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

__doc__ = 'Sets the revision visibility parameter to None for all revisions.'

__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Transaction, RevisionVisibility

doc = __revit__.ActiveUIDocument.Document

revs = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()

with Transaction(doc, 'Turn off Revisions') as t:
    t.Start()
    for rev in revs:
        rev.Visibility = RevisionVisibility.Hidden
    t.Commit()
