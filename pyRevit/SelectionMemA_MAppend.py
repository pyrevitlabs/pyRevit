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

selection = { elId.ToString() for elId in uidoc.Selection.GetElementIds() }

try: 
	f = open(datafile, 'r')
	prevsel = pl.load(f)
	newsel = prevsel.union( selection )
	f.close()
	f = open(datafile, 'w')
	pl.dump(newsel, f)
	f.close()
except:
	f = open(datafile, 'w')
	pl.dump( selection, f)
	f.close()
