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

__doc__ = 'Applies the copied Visibility Graphics settings to the active view.'

__window__.Hide()
from Autodesk.Revit.DB import ElementId, Transaction
from System.Collections.Generic import List

import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveVisibilityGraphicsState.pym'

try:
    f = open(datafile, 'r')
    id = pl.load(f)
    f.close()
    with Transaction(doc, 'Paste Visibility Graphics') as t:
        t.Start()
        uidoc.ActiveGraphicalView.ApplyViewTemplateParameters(doc.GetElement(ElementId(id)))
        t.Commit()
    __window__.Close()
except:
    __window__.Show()
    print('CAN NOT FIND ANY VISIBILITY GRAPHICS SETTINGS IN MEMORY:\n{0}'.format(datafile))
