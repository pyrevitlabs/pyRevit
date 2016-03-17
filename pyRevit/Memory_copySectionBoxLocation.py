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

__doc__ = '''Copy the Section Box settings of the active 3D view to memory.'''


__window__.Close()
from Autodesk.Revit.DB import ElementId, View3D
from Autodesk.Revit.UI import TaskDialog

import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

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

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveSectionBoxState.pym'

av = uidoc.ActiveGraphicalView
avui = uidoc.GetOpenUIViews()[0]

if isinstance( av, View3D ):
	sb = av.GetSectionBox()
	viewOrientation = av.GetOrientation()

	sbox = bbox()
	sbox.minx = sb.Min.X
	sbox.miny = sb.Min.Y
	sbox.minz = sb.Min.Z
	sbox.maxx = sb.Max.X
	sbox.maxy = sb.Max.Y
	sbox.maxz = sb.Max.Z

	vo = vorient()
	vo.eyex = viewOrientation.EyePosition.X
	vo.eyey = viewOrientation.EyePosition.Y
	vo.eyez = viewOrientation.EyePosition.Z
	vo.forwardx = viewOrientation.ForwardDirection.X
	vo.forwardy = viewOrientation.ForwardDirection.Y
	vo.forwardz = viewOrientation.ForwardDirection.Z
	vo.upx = viewOrientation.UpDirection.X
	vo.upy = viewOrientation.UpDirection.Y
	vo.upz = viewOrientation.UpDirection.Z

	f = open(datafile, 'w')
	pl.dump( sbox , f)
	pl.dump( vo , f)
	f.close()
else:
	TaskDialog.Show('RevitPythonShell', 'You must be on a 3D view to copy Section Box settings.')
