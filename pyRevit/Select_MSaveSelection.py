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
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.sel'
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