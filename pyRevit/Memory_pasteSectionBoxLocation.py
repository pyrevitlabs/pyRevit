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

__doc__ = '''Apply the copied Section Box settings to the active 3D view.'''

__window__.Hide()
from Autodesk.Revit.DB import ElementId, Transaction, BoundingBoxXYZ, XYZ, View3D, ViewOrientation3D
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

import os
import os.path as op
import pickle as pl

class point:
	x = 0
	y = 0

class bbox():
	minx = 0
	miny = 0
	minz = 0
	maxx = 0
	maxy = 0
	maxz = 0

class vorient():
	eyex = 0
	eyey = 0
	eyez = 0
	forwardx = 0
	forwardy = 0
	forwardz = 0
	upx = 0
	upy = 0
	upz = 0

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveSectionBoxState.pym'

try:
	f = open(datafile, 'r')
	sbox = pl.load(f)
	vo = pl.load(f)
	f.close()

	sb = BoundingBoxXYZ()
	sb.Min = XYZ( sbox.minx, sbox.miny, sbox.minz )
	sb.Max = XYZ( sbox.maxx, sbox.maxy, sbox.maxz )

	vor = ViewOrientation3D(	XYZ( vo.eyex , vo.eyey, vo.eyez ),
								XYZ( vo.upx , vo.upy, vo.upz ),
								XYZ( vo.forwardx , vo.forwardy, vo.forwardz ) )

	av = uidoc.ActiveGraphicalView
	avui = uidoc.GetOpenUIViews()[0]
	if isinstance( av, View3D ):
		with Transaction(doc, 'Paste Section Box Settings') as t:
			t.Start()
			av.SetSectionBox( sb )
			av.SetOrientation( vor )
			t.Commit()
		avui.ZoomToFit()
	else:
		TaskDialog.Show('pyRevit', 'You must be on a 3D view to paste Section Box settings.')
	__window__.Close()
except:
	__window__.Show()
	print('CAN NOT FIND ANY VISIBILITY GRAPHICS SETTINGS IN MEMORY:\n{0}'.format(datafile))

