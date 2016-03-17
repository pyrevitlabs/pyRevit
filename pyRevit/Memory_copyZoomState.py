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

__doc__ = '''Copy the zoom state of the active view to memory.'''


__window__.Close()
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

av = uidoc.GetOpenUIViews()[0]
cornerlist = av.GetZoomCorners()

vc1 = cornerlist[0]
vc2 = cornerlist[1]
p1 = point()
p2 = point()
p1.x = vc1.X
p1.y = vc1.Y
p2.x = vc2.X
p2.y = vc2.Y

f = open(datafile, 'w')
pl.dump( p1, f)
pl.dump( p2, f)
f.close()
