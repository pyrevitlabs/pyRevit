'''
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
'''

__doc__ = 'Saves current selection memory as a Selection Filter.'

__window__.Close()
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.DB import SelectionFilterElement

import os
import os.path as op
import pickle as pl
from datetime import datetime

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.pym'
f = open(datafile, 'r')

cursel = pl.load(f)
f.close()

filtername = 'SavedSelection_' + prjname + '_' + str(datetime.now())

t = Transaction(doc, 'pySaveSelection')
t.Start()
selFilter = SelectionFilterElement.Create(doc, filtername )
for elid in cursel:
	selFilter.AddSingle( ElementId( int(elid) ) )
t.Commit()