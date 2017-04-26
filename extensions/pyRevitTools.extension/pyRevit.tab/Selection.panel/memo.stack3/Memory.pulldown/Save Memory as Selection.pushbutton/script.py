"""Saves current selection memory as a Selection Filter."""

import os
import os.path as op
import pickle as pl

from pyrevit.coreutils import timestamp
from revitutils import doc
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.DB import SelectionFilterElement

usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.pym'
f = open(datafile, 'r')

cursel = pl.load(f)
f.close()

filtername = 'SavedSelection_' + prjname + '_' + timestamp()

t = Transaction(doc, 'pySaveSelection')
t.Start()
selFilter = SelectionFilterElement.Create(doc, filtername)
for elid in cursel:
    selFilter.AddSingle(ElementId(int(elid)))
t.Commit()
