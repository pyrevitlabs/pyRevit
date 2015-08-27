__doc__ = 'Clears selection from memory. Works like the MC button in a calculator. This is a project-dependent (Revit *.rvt) memory. Every project has its own memory saved in user temp folder as *.sel files.'

__window__.Close()
#from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import SelElementSet

import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.sel'
f = open(datafile, 'wb')
prevsel = set([])
pl.dump( prevsel, f)
f.close()

