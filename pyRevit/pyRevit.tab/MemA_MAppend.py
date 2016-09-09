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

__doc__ = 'Append current selection to memory. Works like the M+ button in a calculator. This is a project-dependent (Revit *.rvt) memory. Every project has its own memory saved in user temp folder as *.pym files.'

__window__.Close()
# from Autodesk.Revit.DB import ElementId
import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.pym'

selection = {elId.ToString() for elId in uidoc.Selection.GetElementIds()}

try:
    f = open(datafile, 'r')
    prevsel = pl.load(f)
    newsel = prevsel.union(selection)
    f.close()
    f = open(datafile, 'w')
    pl.dump(newsel, f)
    f.close()
except:
    f = open(datafile, 'w')
    pl.dump(selection, f)
    f.close()
