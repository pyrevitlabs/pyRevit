__window__.Hide()
from Autodesk.Revit.DB import ElementId
from System.Collections.Generic import List

import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.sel'
try:
	f = open(datafile, 'r')
	cursel = pl.load(f)
	f.close()

	set = []
	for elId in cursel:
		set.append( ElementId( int( elId )))

	uidoc.Selection.SetElementIds( List[ElementId]( set ) )

except:
	__window__.Show()
	print('CAN NOT FIND SELECTION FILE:\n{0}'.format(datafile))