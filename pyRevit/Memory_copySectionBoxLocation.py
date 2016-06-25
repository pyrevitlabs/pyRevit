"""
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
"""

__doc__ = 'Copies the section box boundary and orientation of the active 3D view to memory.'

__window__.Close()
from Autodesk.Revit.DB import ElementId, View3D
from Autodesk.Revit.UI import TaskDialog

import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


class BBox:
    def __init__(self):
        self.minx = 0
        self.miny = 0
        self.minz = 0
        self.maxx = 0
        self.maxy = 0
        self.maxz = 0


class ViewOrient:
    def __init__(self):
        self.eyex = 0
        self.eyey = 0
        self.eyez = 0
        self.forwardx = 0
        self.forwardy = 0
        self.forwardz = 0
        self.upx = 0
        self.upy = 0
        self.upz = 0


usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]
datafile = usertemp + '\\' + prjname + '_pySaveSectionBoxState.pym'

av = uidoc.ActiveGraphicalView
avui = uidoc.GetOpenUIViews()[0]

if isinstance(av, View3D):
    sb = av.GetSectionBox()
    viewOrientation = av.GetOrientation()

    sbox = BBox()
    sbox.minx = sb.Min.X
    sbox.miny = sb.Min.Y
    sbox.minz = sb.Min.Z
    sbox.maxx = sb.Max.X
    sbox.maxy = sb.Max.Y
    sbox.maxz = sb.Max.Z

    vo = ViewOrient()
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
    pl.dump(sbox, f)
    pl.dump(vo, f)
    f.close()
else:
    TaskDialog.Show('pyRevit', 'You must be on a 3D view to copy Section Box settings.')
