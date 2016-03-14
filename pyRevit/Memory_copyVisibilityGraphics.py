__doc__ = '''Copy the Visibility Graphics settings of the active view to memory.'''


__window__.Close()
import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveVisibilityGraphicsState.pym'

av = uidoc.ActiveGraphicalView

f = open(datafile, 'w')
pl.dump( int( av.Id.IntegerValue) , f)
f.close()
