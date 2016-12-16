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

__doc__ = 'Brings selected object to Front of the current view. This only works on elements that support this option.'

__window__.Close()
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import DetailElementOrderUtils as eo

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

with Transaction(doc, 'Bring Selected To Front') as t:
    t.Start()
    for elId in uidoc.Selection.GetElementIds():
        try:
            eo.BringForward(doc, doc.ActiveView, elId)
        except:
            continue
    t.Commit()
