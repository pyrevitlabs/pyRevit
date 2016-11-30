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

__doc__ = 'Read selection from memory. Works like the MR button in a calculator. This is a project-dependent (Revit *.rvt) memory. Every project has its own memory saved in user temp folder as *.pym files.'

import os
import os.path as op
import pickle as pl

from Autodesk.Revit.DB import ElementId
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.pym'
try:
    f = open(datafile, 'r')
    cursel = pl.load(f)
    f.close()

    set = []
    for elId in cursel:
        set.append(ElementId(int(elId)))

    uidoc.Selection.SetElementIds(List[ElementId](set))
    __window__.Close()
except:
    __window__.Show()
    print('CAN NOT FIND SELECTION FILE:\n{0}'.format(datafile))
