__doc__ = '''Apply the copied zoom state to the active view.'''

__window__.Hide()
from Autodesk.Revit.DB import ElementId, XYZ
# from Autodesk.Revit.UI import Rectangle
from System.Collections.Generic import List

import os
import os.path as op
import pickle as pl

class point:
	x = 0
	y = 0

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitActiveViewZoomState.pym'
try:
	f = open(datafile, 'r')
	p2 = pl.load(f)
	p1 = pl.load(f)
	f.close()
	vc1 = XYZ( p1.x, p1.y, 0 )
	vc2 = XYZ( p2.x, p2.y, 0 )
	av = uidoc.GetOpenUIViews()[0]
	av.ZoomAndCenterRectangle(vc1, vc2)
except:
	__window__.Show()
	print('CAN NOT FIND ZOOM STATE FILE:\n{0}'.format(datafile))