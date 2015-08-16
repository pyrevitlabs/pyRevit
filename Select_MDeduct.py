__window__.Close()
# from Autodesk.Revit.DB import ElementId
import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.sel'

selection = { el.Id.ToString() for el in uidoc.Selection.Elements }

try: 
	f = open(datafile, 'r')
	prevsel = pl.load(f)
	newsel = prevsel.difference( selection )
	f.close()
	f = open(datafile, 'w')
	pl.dump(newsel, f)
	f.close()
except:
	f = open(datafile, 'w')
	prevsel = set([])
	pl.dump( prevsel, f)
	f.close()
