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

__doc__ = 'Reorients the current 3D view camera, perpendicular to the selected face. ' \
          'This tool will set a sketch plane over the selected face for 3d drawing.'

__window__.Close()
from Autodesk.Revit.DB import Transaction, View3D, SketchPlane, Plane
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

curview = uidoc.ActiveView
try:
    ref = uidoc.Selection.PickObject(ObjectType.Face)
    el = doc.GetElement(ref.ElementId)
    face = el.GetGeometryObjectFromReference(ref)
    if isinstance(curview, View3D):
        t = Transaction(doc, 'Orient to Selected Face')
        t.Start()
        sp = SketchPlane.Create(doc, Plane(face.Normal, face.Origin))
        curview.OrientTo(face.Normal.Negate())
        uidoc.ActiveView.SketchPlane = sp
        uidoc.RefreshActiveView()
        t.Commit()
except:
    pass
